"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""

import json
from datetime import date, datetime

import pandas as pd
from predibench.agent.models import (
    DataPoint,
    ModelInfo,
    ModelInvestmentDecisions,
)
from predibench.backend.data_loader import (
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.data_model import (
    BackendData,
    EventBackend,
    EventDecisionPnlBackend,
    FullModelResult,
    ModelPerformanceBackend,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import get_historical_returns
from predibench.logger_config import get_logger
from predibench.storage_utils import file_exists_in_storage, read_from_storage
from predibench.utils import string_to_date

logger = get_logger(__name__)


def _to_date_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with index converted to Python date objects.

    Ensures consistent comparisons and intersections between positions (date)
    and prices indices. Duplicates (same day) keep the last value.
    """
    if df is None or len(df.index) == 0:
        return df
    new_index: list[date] = []
    for idx in df.index:
        if isinstance(idx, datetime):
            new_index.append(idx.date())
        elif hasattr(idx, "date") and not isinstance(idx, date):
            # e.g., pandas Timestamp
            new_index.append(idx.date())
        else:
            new_index.append(idx)
    df2 = df.copy()
    df2.index = pd.Index(new_index)
    # remove duplicates by keeping last
    df2 = df2[~df2.index.duplicated(keep="last")]
    return df2


def get_data_for_backend() -> BackendData:
    """
    Pre-compute all data needed for backend API endpoints.

    This function loads all data sources only once and computes everything needed
    for maximum performance at runtime.
    """
    logger.info("Starting comprehensive backend data computation...")

    # Step 1: Load all base data sources (load once, use everywhere)
    logger.info("Loading base data sources...")
    model_decisions = load_investment_choices_from_google()  # Load once
    _saved_events = load_saved_events()  # Load once
    events = get_non_duplicated_events(_saved_events)
    logger.info("Loading market prices...")
    market_prices = load_market_prices(events)  # Load once
    prices_df = get_historical_returns(market_prices)  # Load once
    prices_df = prices_df.sort_index()
    # prices_df = prices_df.resample("D").last()  # Do this BEFORE _to_date_index
    prices_df = _to_date_index(prices_df)

    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]

    # Step 2: Compute ModelPerformanceBackend for each model
    logger.info("Computing model performance data (per day + per event)...")
    model_decisions, performance_per_model = _compute_model_performance(
        prices_df=prices_df,
        backend_events=backend_events,
        model_decisions=model_decisions,
    )

    # Step 3: Compute leaderboard from performance
    logger.info("Building leaderboard from performance data...")
    leaderboard = get_leaderboard(list(performance_per_model.values()))

    logger.info("Finished computing comprehensive backend data!")

    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance_per_model=performance_per_model,
        model_decisions=model_decisions,
    )


class ModelSummaryInfo:
    def __init__(self):
        self.trades_dates = set()
        self.trade_count = 0
        self.pnl_per_event_decision = {}
        self.brier_scores = {}


def _compute_model_performance(
    prices_df: pd.DataFrame,
    backend_events: list[EventBackend],
    model_decisions: list[ModelInvestmentDecisions],
) -> tuple[list[ModelInvestmentDecisions], dict[str, ModelPerformanceBackend]]:
    """Compute performance data (cumulative profit and brier score) for each model.

    Produces per-model cumulative PnL (overall/event/market) and Brier scores
    (overall/event/market) as time series, along with summary metrics.
    """
    # Map market -> event for aggregations
    market_to_event: dict[str, str] = {}
    for event in backend_events:
        for market in event.markets:
            market_to_event[market.id] = event.id

    all_model_ids: set[tuple[str, str]] = {
        (decision.model_id, decision.model_info.model_pretty_name)
        for decision in model_decisions
    }

    model_decision_additional_info: dict[str, ModelSummaryInfo] = {
        model_id: ModelSummaryInfo() for model_id, _ in all_model_ids
    }
    cutoff = date(2025, 8, 1)

    # Filter rows strictly after August 1
    prices_df = prices_df[prices_df.index > cutoff]
    prices_df = prices_df.sort_index()

    trade_dates_per_model: dict[str, set[date]] = {
        model_id: set() for model_id, _ in all_model_ids
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

    # Get per-event performance
    for model_decision in model_decisions:
        # NOTE: is it really necessary to deduplicate "multiple decisions for the same market on the same date" : does it really happen?
        for event_decision in model_decision.event_investment_decisions:
            net_gains_per_market = []
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

            for market_decision in event_decision.market_investment_decisions:
                if (
                    model_decision.target_date
                    not in prices_df[market_decision.market_id].dropna().index
                ):
                    # NOTE: market decision should not be done after when the market is not open yet/closed
                    continue

                market_prices = prices_df[market_decision.market_id].ffill().copy()
                latest_price = float(market_prices.ffill().iloc[-1])
                market_decision.brier_score_pair_current = (
                    latest_price,
                    market_decision.decision.odds,
                )
                if market_decision.decision.bet == 0:
                    continue
                assert (
                    min(market_prices.fillna(0)) >= 0
                    and max(market_prices.fillna(0)) <= 1
                ), "Market prices must be between 0 and 1, got: " + str(market_prices)

                if market_decision.decision.bet < 0:
                    market_prices = 1 - market_prices

                import numpy as np

                market_prices = market_prices.bfill().ffill()
                price_at_decision = market_prices.loc[model_decision.target_date]

                if price_at_decision == 0:
                    raise ValueError("Price at decision is 0!")

                # Cut market prices betweend dates.
                if next_decision_date is not None:
                    market_prices = market_prices.loc[decision_date:next_decision_date]
                else:
                    market_prices = market_prices.loc[decision_date:]

                net_gains_until_next_decision = (
                    market_prices.fillna(0) / price_at_decision - 1
                ) * abs(market_decision.decision.bet)
                assert np.min(net_gains_until_next_decision) >= -abs(
                    market_decision.decision.bet
                ), "Cannot lose more than the bet, got: " + str(
                    net_gains_until_next_decision
                )

                # Preserve market_id as column name, make name unique by adding the target date
                net_gains_until_next_decision.name = (
                    market_decision.market_id
                    + "_"
                    + model_decision.target_date.strftime("%Y-%m-%d")
                )

                net_gains_per_market.append(net_gains_until_next_decision)

                # Gain, brier score, trade count
                market_decision.net_gains_at_decision_end = (
                    net_gains_until_next_decision.iloc[-1]
                )

                if market_decision.decision.bet != 0:
                    model_decision_additional_info[
                        model_decision.model_id
                    ].trade_count += 1
                model_decision_additional_info[model_decision.model_id].brier_scores[
                    market_decision.market_id
                ] = (latest_price, market_decision.decision.odds)

            # Aggregate market gains to get the event gain
            if len(net_gains_per_market) > 0:
                net_gains_for_event_df = pd.concat(net_gains_per_market, axis=1)
            else:
                net_gains_for_event_df = pd.DataFrame(index=prices_df.index)

            sum_net_gains_for_event_df = net_gains_for_event_df.sum(axis=1) / 10

            model_decision_additional_info[model_decision.model_id].trades_dates.add(
                model_decision.target_date.strftime("%Y-%m-%d")
            )
            model_decision_additional_info[
                model_decision.model_id
            ].pnl_per_event_decision[
                event_decision.event_id
            ] = sum_net_gains_for_event_df

            event_decision.net_gains_until_next_decision = (
                DataPoint.list_datapoints_from_series(
                    sum_net_gains_for_event_df,
                )
            )

    # Get each model's daily performance (per decision batch)
    model_performances: dict[str, ModelPerformanceBackend] = {}
    for model_id, model_name in all_model_ids:
        # Map decision date -> list of event_ids for that model on that date
        decisions_for_model = [d for d in model_decisions if d.model_id == model_id]
        decisions_for_model.sort(key=lambda d: d.target_date)
        events_by_date: dict[date, list[str]] = {}
        for d in decisions_for_model:
            events_by_date[d.target_date] = [
                e.event_id for e in d.event_investment_decisions
            ]

        # Event-level net gains already scaled to portfolio share (1/10) and
        # time-limited to [decision_date, next_decision_date]
        pnl_series_by_event: dict[str, pd.Series] = model_decision_additional_info[
            model_id
        ].pnl_per_event_decision

        # Build portfolio value over time by compounding batch returns
        portfolio_values: dict[date, float] = {}
        current_value: float = 1.0

        for batch_date in sorted(events_by_date.keys()):
            event_ids = events_by_date.get(batch_date, [])
            event_series_list: list[pd.Series] = [
                pnl_series_by_event[eid]
                for eid in event_ids
                if eid in pnl_series_by_event
            ]

            if len(event_series_list) == 0:
                # No active events in this batch; portfolio stays flat on batch_date
                portfolio_values[batch_date] = current_value
                continue

            # Sum per-event net gains to get batch cumulative return (relative to batch start)
            batch_net_gains = pd.concat(event_series_list, axis=1).sum(axis=1)
            batch_net_gains = batch_net_gains.sort_index()

            # Convert to portfolio value within the batch and record
            for time, net_gain in batch_net_gains.items():
                v = current_value * (1.0 + float(net_gain))
                portfolio_values[time] = v

            # Move to next batch with compounded value at end of window
            current_value = current_value * (1.0 + float(batch_net_gains.iloc[-1]))

        if len(portfolio_values) > 0:
            portfolio_series = pd.Series(portfolio_values).sort_index()
            net_profit = (portfolio_series - 1.0).ffill()
            final_profit = float(net_profit.iloc[-1])
        else:
            net_profit = pd.Series(dtype=float)
            final_profit = 0.0

        brier_scores = model_decision_additional_info[model_id].brier_scores.values()
        final_brier_score = (
            sum([(a - b) ** 2 for a, b in brier_scores]) / len(brier_scores)
            if len(brier_scores) > 0
            else 1.0
        )

        model_performances[model_id] = ModelPerformanceBackend(
            model_id=model_id,
            model_name=model_name,
            trades_count=model_decision_additional_info[model_id].trade_count,
            trades_dates=sorted(
                list(model_decision_additional_info[model_id].trades_dates),
            ),
            pnl_per_event_decision={
                event_id: EventDecisionPnlBackend(
                    event_id=event_id,
                    pnl=DataPoint.list_datapoints_from_series(pnl),
                )
                for event_id, pnl in model_decision_additional_info[
                    model_id
                ].pnl_per_event_decision.items()
            },
            pnl_history=DataPoint.list_datapoints_from_series(net_profit),
            final_profit=final_profit,
            final_brier_score=final_brier_score,
        )

    return model_decisions, model_performances


def load_full_result_from_bucket(
    model_id: str, event_id: str, target_date: str
) -> FullModelResult | None:
    """Load a single full result from cache file."""
    model_result_path = ModelInfo.static_get_model_result_path(
        model_id=model_id, target_date=string_to_date(target_date)
    )
    cache_file_path = model_result_path / f"{event_id}_full_response.json"

    if file_exists_in_storage(cache_file_path):
        full_result_text = read_from_storage(cache_file_path)
        try:
            # First try to parse as FullModelResult (new format)
            result_data = json.loads(full_result_text)

            # Check if it's already a FullModelResult structure
            if isinstance(result_data, dict) and all(
                key in result_data
                for key in [
                    "model_id",
                    "event_id",
                    "target_date",
                    "full_result_listdict",
                ]
            ):
                # New format: directly parse as FullModelResult
                # Handle backward compatibility for files without agent_type field
                if "agent_type" not in result_data:
                    result_data["agent_type"] = None
                return FullModelResult.model_validate(result_data)
            else:
                # Old format: result_data is the raw full_result_listdict
                # Handle both list and dict formats and remove model_input_messages
                if isinstance(result_data, list):
                    # list format: remove model_input_messages from each step
                    for step in result_data:
                        if isinstance(step, dict) and "model_input_messages" in step:
                            del step["model_input_messages"]
                elif isinstance(result_data, dict):
                    # Dict format: remove model_input_messages if present
                    if "model_input_messages" in result_data:
                        del result_data["model_input_messages"]

                return FullModelResult(
                    model_id=model_id,
                    event_id=event_id,
                    target_date=str(target_date),
                    agent_type=None,  # Default for old files
                    full_result_listdict=result_data,
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            # If parsing fails, return None
            return None
    return None


if __name__ == "__main__":
    get_data_for_backend()
