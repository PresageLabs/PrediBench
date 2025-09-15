"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""

import json
from datetime import date
from datetime import datetime as dt
from typing import List

import pandas as pd
from predibench.agent.models import ModelInfo, ModelInvestmentDecisions
from predibench.backend.brier import compute_brier_scores_df
from predibench.backend.data_loader import (
    load_agent_position,
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.data_model import (
    BackendData,
    EventBackend,
    EventPnlBackend,
    FullModelResult,
    MarketPnlBackend,
    ModelPerformanceBackend,
    TimeseriesPointBackend,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import compute_pnl_series_per_model, get_historical_returns
from predibench.storage_utils import file_exists_in_storage, read_from_storage
from predibench.utils import date_to_string, string_to_date


def _to_date_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with index converted to Python date objects.

    Ensures consistent comparisons and intersections between positions (date)
    and prices indices. Duplicates (same day) keep the last value.
    """
    if df is None or len(df.index) == 0:
        return df
    new_index: list[date] = []
    for idx in df.index:
        if isinstance(idx, dt):
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
    print("Starting comprehensive backend data computation...")

    # Step 1: Load all base data sources (load once, use everywhere)
    print("Loading base data sources...")
    model_results = load_investment_choices_from_google()  # Load once
    _saved_events = load_saved_events()  # Load once
    events = get_non_duplicated_events(_saved_events)
    positions_df = load_agent_position(model_results)  # Load once - pass model_results
    market_prices = load_market_prices(events)  # Load once
    prices_df = get_historical_returns(market_prices)  # Load once
    prices_df = _to_date_index(prices_df)

    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]

    # Step 2: Compute ModelPerformanceBackend for each model
    print("Computing model performance data (PnL + Brier)...")
    performance = _compute_model_performance_list(
        positions_df=positions_df,
        prices_df=prices_df,
        backend_events=backend_events,
        model_results=model_results,
    )
    performance_per_bet = _compute_model_performance_list(
        positions_df=positions_df,
        prices_df=prices_df,
        backend_events=backend_events,
        model_results=model_results,
        by_bet=True,
    )

    # Step 3: Compute leaderboard from performance
    print("Building leaderboard from performance data...")
    leaderboard = get_leaderboard(performance)

    print("Finished computing comprehensive backend data!")

    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance_per_day=performance,
        performance_per_bet=performance_per_bet,
        model_results=model_results,
    )


def _compute_model_performance_list(
    positions_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    backend_events: List[EventBackend],
    model_results: List[ModelInvestmentDecisions],
    by_bet: bool = False,
) -> List[ModelPerformanceBackend]:
    """Compute ModelPerformanceBackend data for each model.

    Produces per-model cumulative PnL (overall/event/market) and Brier scores
    (overall/event/market) as time series, along with summary metrics.
    """
    # Map market -> event for aggregations
    market_to_event: dict[str, str] = {}
    for ev in backend_events:
        for m in ev.markets:
            market_to_event[m.id] = ev.id

    # Pre-compute events by id for iteration
    events_by_id = {e.id: e for e in backend_events}

    performance_list: list[ModelPerformanceBackend] = []

    # Iterate unique models by model_id
    for model_id in positions_df["model_id"].unique():
        # Filter positions/predictions for this model
        model_positions = positions_df[positions_df["model_id"] == model_id]
        # Get the model_name for this model_id (they should be consistent within a model_id)
        model_name = model_positions["model_name"].iloc[0]

        # Trades metadata
        trade_rows = model_positions[model_positions["choice"] != 0]
        trade_dates = sorted({str(d) for d in trade_rows["date"].unique()})
        trades_count = int(len(trade_rows))

        # Handle duplicates by keeping the last entry (most recent decision)
        # This handles cases where the same model made multiple decisions for the same market on the same date
        model_positions_deduped = model_positions.drop_duplicates(
            subset=["date", "market_id"], keep="last"
        )

        # Pivot to date x market for positions and predictions
        positions_pivot = model_positions_deduped.pivot(
            index="date", columns="market_id", values="choice"
        )
        decisions_pivot = model_positions_deduped.pivot(
            index="date", columns="market_id", values="odds"
        )

        # Choose price index: daily or bet dates (plus final for closure)
        if by_bet:
            bet_dates = list(positions_pivot.index)
            if len(prices_df.index) > 0:
                final_date = prices_df.index.max()
                price_index = sorted(set(bet_dates + [final_date]))
            else:
                price_index = sorted(set(bet_dates))
            prices_for_calc = prices_df.reindex(price_index, method="ffill")
        else:
            prices_for_calc = prices_df

        # Compute PnL series
        portfolio_cum_pnl, market_cum_pnls = compute_pnl_series_per_model(
            positions_agent_df=positions_pivot, prices_df=prices_for_calc
        )

        # If per-bet, fold final move back onto last bet so index shows only bet dates
        if by_bet:
            bet_index = pd.Index(sorted(positions_pivot.index))
            if len(portfolio_cum_pnl) > 0:
                portfolio_cum_pnl = portfolio_cum_pnl.reindex(bet_index, method="ffill")
            market_cum_pnls = {
                m_id: (s.reindex(bet_index, method="ffill") if len(s) > 0 else s)
                for m_id, s in market_cum_pnls.items()
            }

        # Convert overall cumulative pnl to backend points
        overall_cum_pnl_points = [
            TimeseriesPointBackend(
                date=(date_to_string(idx) if hasattr(idx, "strftime") else str(idx)),
                value=float(val),
            )
            for idx, val in portfolio_cum_pnl.items()
        ]

        # Market-level PnL to backend
        market_pnls_backend: list[MarketPnlBackend] = []
        for market_id, cum_series in market_cum_pnls.items():
            market_points = [
                TimeseriesPointBackend(
                    date=(
                        date_to_string(idx) if hasattr(idx, "strftime") else str(idx)
                    ),
                    value=float(val),
                )
                for idx, val in cum_series.items()
            ]
            market_pnls_backend.append(
                MarketPnlBackend(market_id=market_id, pnl=market_points)
            )

        # Event-level PnL = sum of cumulative PnL across markets in the event (aligned by date)
        event_pnls_backend: list[EventPnlBackend] = []
        # Build per-event cumulative series
        for event_id, event in events_by_id.items():
            # Gather cumulative series for markets in this event
            series_list = []
            for m in event.markets:
                if m.id in market_cum_pnls:
                    s = market_cum_pnls[m.id]
                    series_list.append(s)
            if not series_list:
                continue
            # Align on union of dates and sum
            aligned = pd.concat(series_list, axis=1).fillna(0.0)
            event_cum = aligned.sum(axis=1)
            event_points = [
                TimeseriesPointBackend(
                    date=(
                        date_to_string(idx) if hasattr(idx, "strftime") else str(idx)
                    ),
                    value=float(val),
                )
                for idx, val in event_cum.items()
            ]
            event_pnls_backend.append(
                EventPnlBackend(event_id=event_id, pnl=event_points)
            )

        # Compute Brier score series
        if by_bet:
            # Include final outcome row for outcome reference
            if len(prices_df.index) > 0:
                final_date = prices_df.index.max()
                brier_index = sorted(set(list(decisions_pivot.index) + [final_date]))
                prices_for_brier = prices_df.reindex(brier_index, method="ffill")
            else:
                prices_for_brier = prices_for_calc
            brier_df_all = compute_brier_scores_df(
                decisions_df=decisions_pivot, prices_df=prices_for_brier
            )
            # Keep only bet dates (rows) in the output
            brier_df = brier_df_all.reindex(decisions_pivot.index)
        else:
            brier_df = compute_brier_scores_df(
                decisions_df=decisions_pivot, prices_df=prices_for_calc
            )

        # Final brier = mean across all available predictions
        final_brier_score = (
            float(brier_df.stack().mean()) if not brier_df.empty else 0.0
        )

        # Build performance object
        performance_list.append(
            ModelPerformanceBackend(
                model_name=model_name,
                model_id=model_id,
                final_pnl=float(portfolio_cum_pnl.iloc[-1])
                if len(portfolio_cum_pnl)
                else 0.0,
                final_brier_score=final_brier_score,
                trades=trades_count,
                trades_dates=trade_dates,
                cummulative_pnl=overall_cum_pnl_points,
                event_pnls=event_pnls_backend,
                market_pnls=market_pnls_backend,
            )
        )

    return performance_list


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
                    # List format: remove model_input_messages from each step
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
