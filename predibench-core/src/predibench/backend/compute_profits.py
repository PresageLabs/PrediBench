"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from predibench.agent.models import ModelInvestmentDecisions
from predibench.backend.data_model import (
    DecisionReturns,
    DecisionSharpe,
    EventDecisionPnlBackend,
    ModelPerformanceBackend,
)
from predibench.common_models import DataPoint
from predibench.logger_config import get_logger

logger = get_logger(__name__)


class ModelSummaryInfo:
    def __init__(self):
        self.trades_dates = set()
        self.trade_count = 0
        self.pnl_per_event_decision = {}
        self.brier_score_pairs = []


def compute_performance_per_decision(
    all_model_ids_names: set[tuple[str, str]],
    model_decisions: list[ModelInvestmentDecisions],
    prices_df: pd.DataFrame,
) -> tuple[list[ModelInvestmentDecisions], dict[str, ModelSummaryInfo]]:
    summary_info_per_model: dict[str, ModelSummaryInfo] = {
        model_id: ModelSummaryInfo() for model_id, _ in all_model_ids_names
    }
    # Get per-event performance
    trade_dates_per_model: dict[str, set[date]] = {
        model_id: set() for model_id, _ in all_model_ids_names
    }
    for model_decision in model_decisions:
        # NOTE: is it really necessary to deduplicate "multiple decisions for the same market on the same date" : does it really happen?
        for event_decision in model_decision.event_investment_decisions:
            trade_dates_per_model[model_decision.model_id].add(
                model_decision.target_date
            )
    ordered_trade_dates_per_model = {
        model_id: sorted(list(trade_dates))
        for model_id, trade_dates in trade_dates_per_model.items()
    }
    for model_decision in model_decisions:
        # NOTE: is it really necessary to deduplicate "multiple decisions for the same market on the same date" : does it really happen?
        decision_date = model_decision.target_date
        index_decision_date = ordered_trade_dates_per_model[
            model_decision.model_id
        ].index(decision_date)
        next_decision_date = (
            ordered_trade_dates_per_model[model_decision.model_id][
                index_decision_date + 1
            ]
            if (
                index_decision_date
                < len(ordered_trade_dates_per_model[model_decision.model_id]) - 1
            )
            else None
        )
        # Collect per-event series to aggregate at the model-decision level
        per_event_series_for_decision: list[pd.Series] = []
        for event_decision in model_decision.event_investment_decisions:
            net_gains_per_market = []
            for market_decision in event_decision.market_investment_decisions:
                # Skip markets that don't have price data, maybe we should renormalize the portfolio
                if market_decision.market_id not in prices_df.columns:
                    continue
                market_series_all = prices_df[market_decision.market_id].copy()
                # Fill missing values to allow robust slicing
                market_prices = market_series_all.ffill().bfill().copy()
                latest_yes_price = float(market_prices.iloc[-1])
                if np.isnan(latest_yes_price):
                    continue
                market_decision.brier_score_pair_current = (
                    latest_yes_price,
                    market_decision.decision.estimated_probability,
                )

                if market_decision.decision.bet == 0:
                    continue
                assert (
                    min(market_prices.fillna(0)) >= 0
                    and max(market_prices.fillna(0)) <= 1
                ), "Market prices must be between 0 and 1, got: " + str(market_prices)

                # Computed signed prices: prices for the chosen outcome
                if market_decision.decision.bet < 0:
                    signed_market_prices = 1 - market_prices
                else:
                    signed_market_prices = market_prices

                # Find first available price on/after the decision date
                if decision_date not in signed_market_prices.index:
                    continue
                signed_price_at_decision = signed_market_prices.loc[decision_date]
                signed_latest_price = signed_market_prices.iloc[-1]

                if float(signed_price_at_decision) == 0 or np.isnan(
                    signed_price_at_decision
                ):
                    # Avoid division by zero; skip this market
                    continue

                # Cut market prices between dates using resolved start index
                if next_decision_date is not None:
                    signed_market_prices = signed_market_prices.loc[
                        decision_date:next_decision_date
                    ]
                else:
                    signed_market_prices = signed_market_prices.loc[decision_date:]
                assert not signed_market_prices.empty, "Sliced market prices are empty"

                net_gains_until_next_decision = (
                    (signed_market_prices / float(signed_price_at_decision) - 1)
                    * abs(market_decision.decision.bet)
                ).fillna(0)
                assert np.min(net_gains_until_next_decision) >= -abs(
                    market_decision.decision.bet
                ), (
                    "Cannot lose more than the bet, got: "
                    + str(net_gains_until_next_decision)
                    + f"for bet {market_decision.decision.bet}"
                )

                # Preserve market_id as column name, make name unique by adding the target date
                net_gains_until_next_decision.name = (
                    market_decision.market_id
                    + "_"
                    + model_decision.target_date.strftime("%Y-%m-%d")
                )

                net_gains_per_market.append(net_gains_until_next_decision)

                # Gain, brier score, trade count
                net_gains_end_value = net_gains_until_next_decision.iloc[-1]
                assert not np.isnan(net_gains_end_value), (
                    f"net_gains_at_decision_end is NaN for market {market_decision.market_id}"
                )
                market_decision.net_gains_at_decision_end = net_gains_end_value

                def get_price_at_horizon(target_date: date) -> float:
                    """Get price at a specific targt date or the latest available price"""
                    future_prices = signed_market_prices.loc[
                        signed_market_prices.index >= target_date
                    ]
                    if future_prices.empty:
                        # If no future prices, use the last available price
                        return signed_market_prices.iloc[-1]
                    else:
                        return future_prices.iloc[0]

                def get_returns(price_at_decision, price_at_expiry) -> float:
                    return (price_at_expiry / float(price_at_decision) - 1) * abs(
                        market_decision.decision.bet
                    )

                summary_info_per_model[
                    model_decision.model_id
                ].brier_score_pairs.append(
                    market_decision.brier_score_pair_current,
                )

                # Store time horizon returns for this market decision
                market_decision.returns = DecisionReturns(
                    one_day_return=get_returns(
                        signed_price_at_decision,
                        get_price_at_horizon(decision_date + timedelta(days=1)),
                    ),
                    two_day_return=get_returns(
                        signed_price_at_decision,
                        get_price_at_horizon(decision_date + timedelta(days=2)),
                    ),
                    seven_day_return=get_returns(
                        signed_price_at_decision,
                        get_price_at_horizon(decision_date + timedelta(days=7)),
                    ),
                    all_time_return=get_returns(
                        signed_price_at_decision, signed_latest_price
                    ),
                )

                if market_decision.decision.bet != 0:
                    summary_info_per_model[model_decision.model_id].trade_count += 1

            # Aggregate market gains to get the event gain
            if len(net_gains_per_market) > 0:
                net_gains_for_event_df = pd.concat(net_gains_per_market, axis=1)
            else:
                net_gains_for_event_df = pd.DataFrame(index=prices_df.index)

            sum_net_gains_for_event_df = net_gains_for_event_df.sum(axis=1) / 10
            # Keep this per-event series to compute the model-level aggregate
            assert sum_net_gains_for_event_df.index.is_monotonic_increasing, (
                "Index is not sorted"
            )
            if not sum_net_gains_for_event_df.empty:
                per_event_series_for_decision.append(sum_net_gains_for_event_df)

            summary_info_per_model[model_decision.model_id].trades_dates.add(
                model_decision.target_date.strftime("%Y-%m-%d")
            )
            summary_info_per_model[model_decision.model_id].pnl_per_event_decision[
                event_decision.event_id
            ] = sum_net_gains_for_event_df

            event_decision.net_gains_until_next_decision = (
                DataPoint.list_datapoints_from_series(
                    sum_net_gains_for_event_df,
                )
            )

            # Aggregate returns at event level from market decisions
            markets_with_returns = [
                market_decision
                for market in event_decision.market_investment_decisions
                if market.returns is not None and market.decision.bet != 0
            ]

            # Total bet is always 1 (including unallocated capital), so no need to normalize here
            event_decision.returns = DecisionReturns(
                one_day_return=sum(
                    market_decision.returns.one_day_return
                    for market_decision in markets_with_returns
                    if market_decision.returns is not None
                ),
                two_day_return=sum(
                    market_decision.returns.two_day_return
                    for market_decision in markets_with_returns
                    if market_decision.returns is not None
                ),
                seven_day_return=sum(
                    market_decision.returns.seven_day_return
                    for market_decision in markets_with_returns
                    if market_decision.returns is not None
                ),
                all_time_return=sum(
                    market_decision.returns.all_time_return
                    for market_decision in markets_with_returns
                    if market_decision.returns is not None
                ),
            )

        # After processing all events for this decision, compute the aggregated
        # portfolio growth across all events (already divided by 10 per event).
        aggregated_series = pd.concat(per_event_series_for_decision, axis=1).sum(axis=1)
        aggregated_series = aggregated_series.reindex(
            prices_df.loc[decision_date:next_decision_date].index
        )  # NOTE: concatenation often breaks index ordering
        model_decision.net_gains_until_next_decision = (
            DataPoint.list_datapoints_from_series(aggregated_series)
        )

    return model_decisions, summary_info_per_model


def compute_performance_per_model(
    all_model_ids_names: set[tuple[str, str]],
    model_decisions: list[ModelInvestmentDecisions],
    summary_info_per_model: dict[str, ModelSummaryInfo],
) -> dict[str, ModelPerformanceBackend]:
    model_performances: dict[str, ModelPerformanceBackend] = {}
    for model_id, model_name in all_model_ids_names:
        # Map decision date -> ModelInvestmentDecisions for this model
        decisions_for_model = [d for d in model_decisions if d.model_id == model_id]
        decisions_for_model.sort(key=lambda d: d.target_date)
        decisions_by_date: dict[date, ModelInvestmentDecisions] = {
            d.target_date: d for d in decisions_for_model
        }

        # Build portfolio value over time by compounding decision returns
        current_compounded_value: float = 1.0
        current_cumulative_value: float = 1.0
        compound_asset_values: list[pd.Series] = []
        cumulative_net_gains: list[pd.Series] = []

        for decision_date in sorted(decisions_by_date.keys()):
            decision = decisions_by_date[decision_date]
            batch_net_gains_series = DataPoint.series_from_list_datapoints(
                decision.net_gains_until_next_decision
            )
            assert batch_net_gains_series is not None

            # Skip processing if no data points (empty series)
            if batch_net_gains_series.empty:
                continue

            current_net_asset_value_compounded = (
                batch_net_gains_series + 1
            ) * current_compounded_value
            current_net_gains_cumulative = (
                batch_net_gains_series + current_cumulative_value
            )

            cumulative_net_gains.append(current_net_gains_cumulative)
            compound_asset_values.append(current_net_asset_value_compounded)
            current_compounded_value = current_net_asset_value_compounded.iloc[-1]
            current_cumulative_value = current_net_gains_cumulative.iloc[-1]

        # Handle case where all decisions had empty data
        if not compound_asset_values:
            # Create empty series with appropriate structure
            compound_asset_values_series = pd.Series(dtype=float)
            cumulative_net_gains_series = pd.Series(dtype=float)
        else:
            compound_asset_values_series = pd.concat(
                compound_asset_values, axis=0
            ).sort_index()
            cumulative_net_gains_series = pd.concat(
                cumulative_net_gains, axis=0
            ).sort_index()
        # Check that duplicate index values are equal
        if compound_asset_values_series.index.has_duplicates:
            assert compound_asset_values_series.groupby(level=0).nunique().max() == 1, (
                "Duplicate index values differ"
            )
            assert cumulative_net_gains_series.groupby(level=0).nunique().max() == 1, (
                "Duplicate index values differ"
            )
        # Deduplicate by keeping only the first occurrence
        compound_asset_values_series = compound_asset_values_series[
            ~compound_asset_values_series.index.duplicated(keep="first")
        ]
        cumulative_net_gains_series = cumulative_net_gains_series[
            ~cumulative_net_gains_series.index.duplicated(keep="first")
        ]
        compound_net_gains_series = compound_asset_values_series - 1.0

        final_profit = compound_net_gains_series.iloc[-1]

        # Calculate average returns across all event decisions for this model
        all_event_returns: dict[str, list[float]] = {
            key: []
            for key in [
                "one_day_return",
                "two_day_return",
                "seven_day_return",
                "all_time_return",
            ]
        }
        for decision in decisions_for_model:
            for event_decision in decision.event_investment_decisions:
                if event_decision.returns is not None:
                    for key in all_event_returns.keys():
                        all_event_returns[key].append(
                            getattr(event_decision.returns, key)
                        )

        # Calculate equal-weighted average returns across all events
        average_returns = DecisionReturns(
            one_day_return=float(np.mean(all_event_returns["one_day_return"])),
            two_day_return=float(np.mean(all_event_returns["two_day_return"])),
            seven_day_return=float(np.mean(all_event_returns["seven_day_return"])),
            all_time_return=float(np.mean(all_event_returns["all_time_return"])),
        )

        # Calculate Sharpe ratios using expectation and volatility of returns per model
        def calculate_sharpe_from_returns(returns_list: list[float]) -> float:
            """Calculate Sharpe ratio from a list of returns using expectation and volatility"""
            if len(returns_list) < 2:
                return 0.0

            returns_array = np.array(returns_list)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array, ddof=1)  # Sample standard deviation

            if std_return == 0 or np.isnan(std_return) or np.isnan(mean_return):
                return 0.0

            # Sharpe ratio = mean return / volatility
            # No need for annualization since returns are already in the correct horizon units
            sharpe = mean_return / std_return
            return float(sharpe)

        # Calculate Sharpe ratios using expectation and volatility of returns
        sharpe = DecisionSharpe(
            one_day_sharpe=calculate_sharpe_from_returns(
                all_event_returns["one_day_return"]
            ),
            two_day_sharpe=calculate_sharpe_from_returns(
                all_event_returns["two_day_return"]
            ),
            seven_day_sharpe=calculate_sharpe_from_returns(
                all_event_returns["seven_day_return"]
            ),
            all_time_sharpe=calculate_sharpe_from_returns(
                all_event_returns["all_time_return"]
            ),
        )

        model_performances[model_id] = ModelPerformanceBackend(
            model_id=model_id,
            model_name=model_name,
            trades_count=summary_info_per_model[model_id].trade_count,
            trades_dates=sorted(
                list(summary_info_per_model[model_id].trades_dates),
            ),
            pnl_per_event_decision={
                event_id: EventDecisionPnlBackend(
                    event_id=event_id,
                    pnl=DataPoint.list_datapoints_from_series(pnl),
                )
                for event_id, pnl in summary_info_per_model[
                    model_id
                ].pnl_per_event_decision.items()
            },
            compound_profit_history=DataPoint.list_datapoints_from_series(
                compound_asset_values_series
            ),
            cumulative_profit_history=DataPoint.list_datapoints_from_series(
                cumulative_net_gains_series
            ),
            average_returns=average_returns,
            sharpe=sharpe,
            final_profit=final_profit,
            final_brier_score=np.mean(
                [
                    (brier_score_pair[0] - brier_score_pair[1]) ** 2
                    for brier_score_pair in summary_info_per_model[
                        model_id
                    ].brier_score_pairs
                ]
            ),
        )
    return model_performances


def recompute_bets_with_kelly_criterion_for_model_decisions(
    model_decisions: list[ModelInvestmentDecisions],
    prices_df: pd.DataFrame,
) -> None:
    for model_decision in model_decisions:
        decision_date = model_decision.target_date
        for event_decision in model_decision.event_investment_decisions:
            event_decision.normalize_investments(
                apply_kelly_criterion_at_date=decision_date,
                market_prices=prices_df,
            )


def _compute_profits(
    prices_df: pd.DataFrame,
    model_decisions: list[ModelInvestmentDecisions],
    recompute_bets_with_kelly_criterion: bool = False,
) -> tuple[list[ModelInvestmentDecisions], dict[str, ModelPerformanceBackend]]:
    """Compute performance data (cumulative profit and brier score) per model decision and per model

    Produces per-model cumulative PnL (overall/event/market) and Brier scores
    (overall/event/market) as time series, along with summary metrics.
    """
    if recompute_bets_with_kelly_criterion:
        recompute_bets_with_kelly_criterion_for_model_decisions(
            model_decisions, prices_df
        )

    all_model_ids_names: set[tuple[str, str]] = {
        (decision.model_id, decision.model_info.model_pretty_name)
        for decision in model_decisions
    }

    # Filter rows strictly after August 1
    cutoff = date(2025, 8, 1)
    prices_df = prices_df[prices_df.index > cutoff]
    prices_df = prices_df.sort_index()

    enriched_model_decisions, summary_info_per_model = compute_performance_per_decision(
        all_model_ids_names=all_model_ids_names,
        model_decisions=model_decisions,
        prices_df=prices_df,
    )

    model_performances: dict[str, ModelPerformanceBackend] = (
        compute_performance_per_model(
            all_model_ids_names=all_model_ids_names,
            model_decisions=enriched_model_decisions,
            summary_info_per_model=summary_info_per_model,
        )
    )
    return enriched_model_decisions, model_performances
