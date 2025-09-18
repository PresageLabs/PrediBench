from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from predibench.agent.models import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInfo,
    ModelInvestmentDecisions,
    SingleInvestmentDecision,
)
from predibench.backend.compute_profits import _compute_profits
from predibench.backend.data_loader import (
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.pnl import get_market_prices_dataframe
from predibench.logger_config import get_logger
from predibench.utils import _to_date_index, apply_template

logger = get_logger(__name__)


@dataclass
class HorizonReturns:
    r1d: float
    r2d: float
    r7d: float
    rall: float


@dataclass
class HorizonBrier:
    b1d: float
    b2d: float
    b7d: float
    ball: float


# Note: per-trade returns and Brier are computed via backend _compute_profits.


def _sharpe(returns: list[float]) -> float:
    arr = np.array(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 2:
        return 0.0
    mu = arr.mean()
    sd = arr.std(ddof=1)
    if sd == 0 or np.isnan(sd) or np.isnan(mu):
        return 0.0
    return float(mu / sd)


def main():
    logger.info("Loading investment choices and market data…")
    model_decisions = load_investment_choices_from_google()
    events = get_non_duplicated_events(load_saved_events())
    market_prices = load_market_prices(events)
    prices_df = get_market_prices_dataframe(market_prices)
    prices_df = prices_df.sort_index()
    prices_df = _to_date_index(prices_df)

    if prices_df is None or prices_df.empty:
        logger.error("No market price data available.")
        return

    logger.info("Building baseline model decisions (most-probable side)…")
    baseline_decisions: list[ModelInvestmentDecisions] = []
    for md in model_decisions:
        decision_date = md.target_date
        new_model_info = ModelInfo(
            model_id=f"{md.model_id}__market_baseline",
            model_pretty_name=f"{md.model_info.model_pretty_name} (baseline)",
            inference_provider=md.model_info.inference_provider,
            company_pretty_name=md.model_info.company_pretty_name,
            open_weights=md.model_info.open_weights,
            agent_type=md.model_info.agent_type,
        )
        new_event_list: list[EventInvestmentDecisions] = []
        for ev in md.event_investment_decisions:
            new_markets: list[MarketInvestmentDecision] = []
            for m in ev.market_investment_decisions:
                mid = m.market_id
                bet_mag = float(abs(m.decision.bet))
                bet_new = 0.0
                est_prob_new = m.decision.estimated_probability
                if mid in prices_df.columns and decision_date in prices_df.index:
                    p_yes = prices_df[mid].ffill().bfill().loc[decision_date]
                    if np.isfinite(p_yes):
                        side = +1 if float(p_yes) >= 0.5 else -1
                        bet_new = side * bet_mag
                        est_prob_new = float(max(p_yes, 1.0 - float(p_yes)))
                new_decision = SingleInvestmentDecision(
                    rationale="Market baseline: bet more-probable side",
                    estimated_probability=est_prob_new,
                    bet=bet_new,
                    confidence=m.decision.confidence,
                )
                new_markets.append(
                    MarketInvestmentDecision(
                        market_id=mid,
                        decision=new_decision,
                        market_question=m.market_question,
                    )
                )
            new_event_list.append(
                EventInvestmentDecisions(
                    event_id=ev.event_id,
                    event_title=ev.event_title,
                    event_description=ev.event_description,
                    market_investment_decisions=new_markets,
                    unallocated_capital=ev.unallocated_capital,
                    token_usage=ev.token_usage,
                    timing=ev.timing,
                    sources_google=ev.sources_google,
                    sources_visit_webpage=ev.sources_visit_webpage,
                )
            )
        baseline_decisions.append(
            ModelInvestmentDecisions(
                model_id=new_model_info.model_id,
                model_info=new_model_info,
                target_date=md.target_date,
                decision_datetime=md.decision_datetime,
                event_investment_decisions=new_event_list,
            )
        )

    # Build a hypothetical variant: force long YES when p_yes < 0.5 for comparison panel
    hypo_long_decisions: list[ModelInvestmentDecisions] = []
    for md in model_decisions:
        decision_date = md.target_date
        new_model_info = ModelInfo(
            model_id=f"{md.model_id}__hypo_long_yes",
            model_pretty_name=f"{md.model_info.model_pretty_name} (hypo long)",
            inference_provider=md.model_info.inference_provider,
            company_pretty_name=md.model_info.company_pretty_name,
            open_weights=md.model_info.open_weights,
            agent_type=md.model_info.agent_type,
        )
        new_event_list: list[EventInvestmentDecisions] = []
        for ev in md.event_investment_decisions:
            new_markets: list[MarketInvestmentDecision] = []
            for m in ev.market_investment_decisions:
                mid = m.market_id
                bet_mag = float(abs(m.decision.bet))
                bet_new = 0.0
                est_prob_new = m.decision.estimated_probability
                if mid in prices_df.columns and decision_date in prices_df.index:
                    p_yes = prices_df[mid].ffill().bfill().loc[decision_date]
                    if np.isfinite(p_yes):
                        # Force long YES for p_yes < 0.5 (else also long)
                        side = +1
                        bet_new = side * bet_mag
                        est_prob_new = float(p_yes)
                new_decision = SingleInvestmentDecision(
                    rationale="Hypothetical: long YES",
                    estimated_probability=est_prob_new,
                    bet=bet_new,
                    confidence=m.decision.confidence,
                )
                new_markets.append(
                    MarketInvestmentDecision(
                        market_id=mid,
                        decision=new_decision,
                        market_question=m.market_question,
                    )
                )
            new_event_list.append(
                EventInvestmentDecisions(
                    event_id=ev.event_id,
                    event_title=ev.event_title,
                    event_description=ev.event_description,
                    market_investment_decisions=new_markets,
                    unallocated_capital=ev.unallocated_capital,
                    token_usage=ev.token_usage,
                    timing=ev.timing,
                    sources_google=ev.sources_google,
                    sources_visit_webpage=ev.sources_visit_webpage,
                )
            )
        hypo_long_decisions.append(
            ModelInvestmentDecisions(
                model_id=new_model_info.model_id,
                model_info=new_model_info,
                target_date=md.target_date,
                decision_datetime=md.decision_datetime,
                event_investment_decisions=new_event_list,
            )
        )

    logger.info("Computing enriched metrics via _compute_profits for baseline…")
    enriched_baseline, _perf_baseline = _compute_profits(
        prices_df=prices_df.copy(), model_decisions=baseline_decisions
    )
    logger.info("Computing enriched metrics for hypothetical long-YES variant…")
    enriched_hypo_long, _ = _compute_profits(
        prices_df=prices_df.copy(), model_decisions=hypo_long_decisions
    )

    # Flatten per-trade metrics from enriched decisions (baseline)
    rows: list[dict] = []
    for md in enriched_baseline:
        decision_date = md.target_date
        for ev in md.event_investment_decisions:
            for m in ev.market_investment_decisions:
                if m.returns is None:
                    continue
                mid = m.market_id
                if mid not in prices_df.columns or decision_date not in prices_df.index:
                    continue
                p_yes = float(prices_df[mid].ffill().bfill().loc[decision_date])
                side = 0
                if m.decision.bet != 0:
                    side = +1 if m.decision.bet > 0 else -1
                rows.append(
                    {
                        "model_id": md.model_id,
                        "event_id": ev.event_id,
                        "market_id": mid,
                        "decision_date": decision_date,
                        "p_yes": p_yes,
                        "bet_size": abs(m.decision.bet),
                        "side": side,
                        # Returns
                        "ret_1d": m.returns.one_day_return,
                        "ret_2d": m.returns.two_day_return,
                        "ret_7d": m.returns.seven_day_return,
                        "ret_all": m.returns.all_time_return,
                        # Brier
                        "brier_1d": m.brier.one_day_brier if m.brier else np.nan,
                        "brier_2d": m.brier.two_day_brier if m.brier else np.nan,
                        "brier_7d": m.brier.seven_day_brier if m.brier else np.nan,
                        "brier_all": m.brier.all_time_brier if m.brier else np.nan,
                    }
                )

    baseline_df = pd.DataFrame(rows)
    if baseline_df.empty:
        logger.error("No baseline trades constructed — check data availability.")
        return

    # Extract hypothetical long returns to compare in p<0.5 bins
    hypo_rows: list[dict] = []
    for md in enriched_hypo_long:
        decision_date = md.target_date
        for ev in md.event_investment_decisions:
            for m in ev.market_investment_decisions:
                if m.returns is None:
                    continue
                hypo_rows.append(
                    {
                        "market_id": m.market_id,
                        "decision_date": decision_date,
                        "hypo_ret_all": m.returns.all_time_return,
                    }
                )
    hypo_df = pd.DataFrame(hypo_rows)
    if not hypo_df.empty:
        baseline_df = baseline_df.merge(
            hypo_df, on=["market_id", "decision_date"], how="left"
        )

    # Aggregate statistics
    agg = {
        "ret_1d": baseline_df["ret_1d"].mean(),
        "ret_2d": baseline_df["ret_2d"].mean(),
        "ret_7d": baseline_df["ret_7d"].mean(),
        "ret_all": baseline_df["ret_all"].mean(),
        "brier_1d": baseline_df["brier_1d"].mean(),
        "brier_2d": baseline_df["brier_2d"].mean(),
        "brier_7d": baseline_df["brier_7d"].mean(),
        "brier_all": baseline_df["brier_all"].mean(),
        "sharpe_1d": _sharpe(baseline_df["ret_1d"].tolist()),
        "sharpe_2d": _sharpe(baseline_df["ret_2d"].tolist()),
        "sharpe_7d": _sharpe(baseline_df["ret_7d"].tolist()),
        "sharpe_all": _sharpe(baseline_df["ret_all"].tolist()),
        "n_trades": len(baseline_df),
    }
    logger.info(f"Baseline aggregate: {agg}")

    # Build one composite figure with subplots
    out_dir = Path("analyses/market_following_strategy_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)

    composite = make_subplots(
        rows=2,
        cols=2,
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
        subplot_titles=(
            "Mean Returns by Horizon",
            "Mean Brier by Horizon",
            "All-time Returns Distribution",
            "",
        ),
    )

    # (1) Mean returns by horizon
    means_ret = pd.DataFrame(
        {
            "horizon": ["1d", "2d", "7d", "all"],
            "mean_return": [
                agg["ret_1d"],
                agg["ret_2d"],
                agg["ret_7d"],
                agg["ret_all"],
            ],
        }
    )
    fig_ret = px.bar(means_ret, x="horizon", y="mean_return")
    for tr in fig_ret.data:
        composite.add_trace(tr, row=1, col=1)
    composite.update_xaxes(title_text="Horizon", row=1, col=1)
    composite.update_yaxes(title_text="Mean return", row=1, col=1)

    # (2) Mean Brier by horizon
    means_brier = pd.DataFrame(
        {
            "horizon": ["1d", "2d", "7d", "all"],
            "mean_brier": [
                agg["brier_1d"],
                agg["brier_2d"],
                agg["brier_7d"],
                agg["brier_all"],
            ],
        }
    )
    fig_brier = px.bar(means_brier, x="horizon", y="mean_brier")
    for tr in fig_brier.data:
        composite.add_trace(tr, row=1, col=2)
    composite.add_hline(y=0.25, line_dash="dash", line_color="red", row=1, col=2)
    composite.update_xaxes(title_text="Horizon", row=1, col=2)
    composite.update_yaxes(title_text="Mean Brier (↓ better)", row=1, col=2)

    # (3) Distribution of all-time returns
    fig_hist = px.histogram(baseline_df, x="ret_all", nbins=60)
    for tr in fig_hist.data:
        composite.add_trace(tr, row=2, col=1)
    composite.update_xaxes(title_text="Per-trade all-time return", row=2, col=1)
    composite.update_yaxes(title_text="Count", row=2, col=1)

    # (Removed) Unlikely YES subplot is shown only in the dedicated figure.

    composite.update_layout(
        title_text="Market Following Strategy Analysis", showlegend=True
    )
    apply_template(composite, width=1400, height=1000)
    composite.write_html(str(out_dir / "market_following_strategy_analysis.html"))

    logger.info(
        "Exported composite study to analyses/market_following_strategy_analysis.html"
    )

    # =============== New Figure: Bias + Unlikely YES boxplots (2x1) ===============
    # Top: average of (realized_outcome - market_price_at_decision) per 0.1 price bin across [0,1]
    # Bottom: Unlikely YES returns by p_yes bin (boxplots) for baseline vs hypothetical long-YES

    def _realized_yes_for_market(mid: str) -> float | np.nan:
        if mid not in prices_df.columns:
            return np.nan
        series = prices_df[mid].dropna()
        if series.empty:
            return np.nan
        final_p = float(series.iloc[-1])
        return 1.0 if final_p >= 0.5 else 0.0

    bias_df = baseline_df.copy()
    # Compute realized outcome per row
    bias_df["realized_yes"] = bias_df["market_id"].apply(_realized_yes_for_market)
    bias_df = bias_df[np.isfinite(bias_df["realized_yes"])].copy()
    bias_df["bias"] = bias_df["realized_yes"] - bias_df["p_yes"]
    bins_full = np.linspace(0.0, 1.0, 11)
    labels_full = [
        f"[{bins_full[i]:.1f},{bins_full[i + 1]:.1f})"
        for i in range(len(bins_full) - 1)
    ]
    bias_df["p_bin"] = pd.cut(
        bias_df["p_yes"],
        bins=bins_full,
        labels=labels_full,
        include_lowest=True,
        right=False,
    )
    bias_stats = (
        bias_df.groupby("p_bin", observed=False)["bias"]
        .mean()
        .reset_index(name="mean_bias")
    )

    fig2 = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.12,
        subplot_titles=(
            "Avg realized − market price by p bin (0.1)",
            "Unlikely YES: Returns by p_yes bin (boxplots)",
        ),
    )

    # Top panel: bias bar chart
    bar_bias = px.bar(
        bias_stats,
        x="p_bin",
        y="mean_bias",
        category_orders={"p_bin": labels_full},
    )
    for tr in bar_bias.data:
        fig2.add_trace(tr, row=1, col=1)
    fig2.add_hline(y=0.0, line_dash="dash", line_color="gray", row=1, col=1)
    fig2.update_xaxes(
        title_text="p_yes at decision (bins)",
        categoryorder="array",
        categoryarray=labels_full,
        row=1,
        col=1,
    )
    fig2.update_yaxes(title_text="Avg (realized − price)", row=1, col=1)

    # Bottom panel: boxplots across all bins (0..1 by 0.1)
    bins_all = np.linspace(0.0, 1.0, 11)
    labels_all = [
        f"[{bins_all[i]:.1f},{bins_all[i + 1]:.1f})" for i in range(len(bins_all) - 1)
    ]
    subset_all = baseline_df.copy()
    if not subset_all.empty:
        subset_all["p_bin"] = pd.cut(
            subset_all["p_yes"],
            bins=bins_all,
            labels=labels_all,
            include_lowest=True,
            right=False,
        )
        # Baseline series (more-probable side)
        base_all = subset_all[np.isfinite(subset_all["ret_all"])].copy()
        base_all["strategy"] = "Baseline (more-probable side)"

        # Hypothetical long-YES series
        hypo_all = subset_all.copy()
        if "hypo_ret_all" in hypo_all.columns:
            hypo_all = hypo_all[np.isfinite(hypo_all["hypo_ret_all"])].copy()
            hypo_all["ret_all"] = hypo_all["hypo_ret_all"]
            hypo_all["strategy"] = "Hypothetical: Long market (YES)"
        else:
            hypo_all = hypo_all.iloc[0:0]

        box_df = pd.concat(
            [
                base_all[["p_bin", "ret_all", "strategy"]],
                hypo_all[["p_bin", "ret_all", "strategy"]],
            ],
            ignore_index=True,
        )
        box_fig = px.box(
            box_df,
            x="p_bin",
            y="ret_all",
            color="strategy",
            category_orders={"p_bin": labels_all},
        )
        for tr in box_fig.data:
            tr.offsetgroup = tr.name  # ensure left-right offset
            fig2.add_trace(tr, row=2, col=1)
        fig2.update_layout(boxmode="group")
        fig2.update_xaxes(
            title_text="Initial p_yes bin (0.1 width, full range)",
            categoryorder="array",
            categoryarray=labels_all,
            row=2,
            col=1,
        )
        fig2.update_yaxes(title_text="All-time return (distribution)", row=2, col=1)
    else:
        fig2.add_annotation(
            text="No data available for boxplots",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.2,
            showarrow=False,
            row=2,
            col=1,
        )

    fig2.update_layout(
        title_text="Market Following Strategy Analysis — Bias and Unlikely YES Distributions",
        showlegend=True,
    )
    apply_template(fig2, width=1400, height=1000)
    fig2.write_html(
        str(out_dir / "market_following_strategy_bias_and_unlikely_boxplots.html")
    )


if __name__ == "__main__":
    main()
