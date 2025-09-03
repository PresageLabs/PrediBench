"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""
from functools import lru_cache
from typing import List
from datetime import datetime
import pandas as pd

from predibench.backend.data_model_new import (
    BackendData, LeaderboardEntryBackend, EventBackend, AgentPerformanceBackend,
    TimeseriesPointBackend, EventPnlBackend, MarketPnlBackend, 
    EventBrierScoreBackend, MarketBrierScoreBackend
)
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.events import get_events_that_received_predictions
from predibench.backend.data_loader import load_investment_choices_from_google, load_saved_events, load_agent_position, load_market_prices
from predibench.backend.pnl import get_all_markets_pnls, get_historical_returns
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
    saved_events = load_saved_events()                     # Load once
    positions_df = load_agent_position(model_results)     # Load once - pass model_results
    market_prices = load_market_prices(saved_events)      # Load once
    prices_df = get_historical_returns(market_prices)     # Load once
    
    # Step 2: Compute core leaderboard and events
    print("Computing core data...")
    leaderboard = get_leaderboard(positions_df, prices_df)
    events = get_events_that_received_predictions(model_results)
    # Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]
    
    # Step 3: Compute AgentPerformanceBackend for each model
    print("Computing agent performance data...")
    pnl_results = get_all_markets_pnls(positions_df, prices_df)
    performance = _compute_agent_performance_list(model_results, leaderboard, pnl_results, positions_df, prices_df, backend_events)
    
    print("Finished computing comprehensive backend data!")
    
    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance=performance,
        model_results=model_results,
    )


def _compute_agent_performance_list(
    model_results: List[ModelInvestmentDecisions],
    leaderboard: List[LeaderboardEntryBackend], 
    pnl_results: dict, 
    positions_df: pd.DataFrame, 
    prices_df: pd.DataFrame,
    backend_events: List[EventBackend]
) -> List[AgentPerformanceBackend]:
    """Compute AgentPerformanceBackend data for each model."""
    
    performance_list = []
    
    # Create leaderboard lookup
    leaderboard_dict = {entry.id: entry for entry in leaderboard}
    
    # Create event and market lookups
    event_dict = {event.id: event for event in backend_events}
    market_dict = {}
    for event in backend_events:
        for market in event.markets:
            market_dict[market.id] = market
    
    for agent_id, pnl_result in pnl_results.items():
        if agent_id not in leaderboard_dict:
            continue
            
        leaderboard_entry = leaderboard_dict[agent_id]
        
        # Get trade dates for this agent
        agent_positions = positions_df[positions_df["model_name"] == agent_id]
        trades_dates = sorted(agent_positions["date"].dt.strftime("%Y-%m-%d").unique().tolist()) if not agent_positions.empty else []
        
        # Convert cumulative PnL to TimeseriesPointBackend
        cummulative_pnl = [TimeseriesPointBackend(date=dp.date, value=dp.value) for dp in pnl_result.cumulative_pnl]
        
        # Compute event-level PnL
        event_pnls = []
        for event_id in event_dict.keys():
            # Get markets for this event
            event_markets = [m.id for m in event_dict[event_id].markets]
            
            # Aggregate PnL for all markets in this event
            event_pnl_series = pd.Series(dtype=float)
            for market_id in event_markets:
                if market_id in pnl_result.market_pnls:
                    market_pnl_series = pd.Series({point.date: point.pnl for point in pnl_result.market_pnls[market_id]})
                    if event_pnl_series.empty:
                        event_pnl_series = market_pnl_series
                    else:
                        event_pnl_series = event_pnl_series.add(market_pnl_series, fill_value=0)
            
            event_pnls.append(EventPnlBackend(
                event_id=event_id,
                pnl=TimeseriesPointBackend.from_series_to_timeseries_points(event_pnl_series)
            ))
        
        # Compute market-level PnL
        market_pnls = []
        for market_id, market_pnl_points in pnl_result.market_pnls.items():
            market_pnl_series = pd.Series({point.date: point.pnl for point in market_pnl_points})
            market_pnls.append(MarketPnlBackend(
                market_id=market_id,
                pnl=TimeseriesPointBackend.from_series_to_timeseries_points(market_pnl_series)
            ))
        
        # Compute Brier scores (placeholder for now - we'll need to implement proper calculation)
        bried_scores = []  # Will be filled with actual Brier score computation
        event_bried_scores = []  # Will be filled with event-level Brier scores
        market_bried_scores = []  # Will be filled with market-level Brier scores
        
        performance_list.append(AgentPerformanceBackend(
            model_name=agent_id,
            final_pnl=leaderboard_entry.final_cumulative_pnl,
            final_brier_score=leaderboard_entry.avg_brier_score,
            trades_dates=trades_dates,
            bried_scores=bried_scores,
            event_bried_scores=event_bried_scores,
            market_bried_scores=market_bried_scores,
            cummulative_pnl=cummulative_pnl,
            event_pnls=event_pnls,
            market_pnls=market_pnls,
        ))
    
    return performance_list



if __name__ == "__main__":
    get_data_for_backend()