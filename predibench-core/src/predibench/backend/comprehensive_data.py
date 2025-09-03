"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""
from functools import lru_cache
from typing import List
from datetime import datetime
import pandas as pd

from predibench.backend.data_model_new import (
    BackendData, LeaderboardEntryBackend, EventBackend, ModelPerformanceBackend,
    TimeseriesPointBackend, EventPnlBackend, MarketPnlBackend, 
    EventBrierScoreBackend, MarketBrierScoreBackend
)
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.data_loader import load_investment_choices_from_google, load_saved_events, load_agent_position, load_market_prices
from predibench.backend.pnl import get_historical_returns, compute_pnl_series_per_model
from predibench.backend.brier import compute_brier_scores_df
from predibench.agent.dataclasses import ModelInvestmentDecisions


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
    _saved_events = load_saved_events()                     # Load once
    events = get_non_duplicated_events(_saved_events)
    positions_df = load_agent_position(model_results)     # Load once - pass model_results
    market_prices = load_market_prices(events)      # Load once
    prices_df = get_historical_returns(market_prices)     # Load once
    
    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]
    
    # Step 2: Compute ModelPerformanceBackend for each model
    print("Computing model performance data (PnL + Brier)...")
    performance = _compute_model_performance_list(
        positions_df=positions_df,
        prices_df=prices_df,
        backend_events=backend_events,
    )

    # Step 3: Compute leaderboard from performance
    print("Building leaderboard from performance data...")
    leaderboard = get_leaderboard(performance)
    
    print("Finished computing comprehensive backend data!")
    
    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance=performance,
        model_results=model_results,
    )


def _compute_model_performance_list(
    positions_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    backend_events: List[EventBackend],
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

    # Iterate unique models by pretty name (as used in positions_df)
    for model_name in positions_df["model_name"].unique():
        # Filter positions/predictions for this model
        model_positions = positions_df[positions_df["model_name"] == model_name]

        # Trades metadata
        trade_rows = model_positions[model_positions["choice"] != 0]
        trade_dates = sorted({str(d) for d in trade_rows["date"].unique()})
        trades_count = int(len(trade_rows))

        # Pivot to date x market for positions and predictions
        positions_pivot = (
            model_positions.pivot(index="date", columns="market_id", values="choice")
        )
        decisions_pivot = (
            model_positions.pivot(index="date", columns="market_id", values="odds")
        )

        # Compute PnL series
        portfolio_cum_pnl, market_cum_pnls = compute_pnl_series_per_model(
            positions_agent_df=positions_pivot, prices_df=prices_df
        )

        # Convert overall cumulative pnl to backend points
        overall_cum_pnl_points = [
            TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in portfolio_cum_pnl.items()
        ]

        # Market-level PnL to backend
        market_pnls_backend: list[MarketPnlBackend] = []
        for market_id, cum_series in market_cum_pnls.items():
            market_points = [
                TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in cum_series.items()
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
                TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in event_cum.items()
            ]
            event_pnls_backend.append(
                EventPnlBackend(event_id=event_id, pnl=event_points)
            )

        # Compute Brier score series
        brier_df = compute_brier_scores_df(decisions_df=decisions_pivot, prices_df=prices_df)

        # Overall per-date brier (mean across markets)
        overall_brier_series = brier_df.mean(axis=1)
        overall_brier_points = [
            TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in overall_brier_series.dropna().items()
        ]
        # Final brier = mean across all available predictions
        final_brier_score = float(brier_df.stack().mean()) if not brier_df.empty else 0.0

        # Market-level brier
        market_brier_backend: list[MarketBrierScoreBackend] = []
        for market_id in brier_df.columns:
            market_series = brier_df[market_id].dropna()
            if market_series.empty:
                continue
            points = [
                TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in market_series.items()
            ]
            market_brier_backend.append(
                MarketBrierScoreBackend(market_id=market_id, brier_score=points)
            )

        # Event-level brier = mean across event's markets per date
        event_brier_backend: list[EventBrierScoreBackend] = []
        for event_id, event in events_by_id.items():
            cols = [m.id for m in event.markets if m.id in brier_df.columns]
            if not cols:
                continue
            ev_series = brier_df[cols].mean(axis=1).dropna()
            ev_points = [
                TimeseriesPointBackend(date=str(idx), value=float(val)) for idx, val in ev_series.items()
            ]
            event_brier_backend.append(
                EventBrierScoreBackend(event_id=event_id, brier_score=ev_points)
            )

        # Build performance object
        performance_list.append(
            ModelPerformanceBackend(
                model_name=model_name,
                final_pnl=float(portfolio_cum_pnl.iloc[-1]) if len(portfolio_cum_pnl) else 0.0,
                final_brier_score=final_brier_score,
                trades_dates=trade_dates,
                bried_scores=overall_brier_points,
                event_bried_scores=event_brier_backend,
                market_bried_scores=market_brier_backend,
                cummulative_pnl=overall_cum_pnl_points,
                event_pnls=event_pnls_backend,
                market_pnls=market_pnls_backend,
                # Inject trades count for leaderboard if model allows extra fields
                **({"trades": trades_count} if True else {}),
            )
        )

    return performance_list



if __name__ == "__main__":
    get_data_for_backend()
