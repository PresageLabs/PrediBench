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
    _saved_events = load_saved_events()                     # Load once
    events = get_non_duplicated_events(_saved_events)
    positions_df = load_agent_position(model_results)     # Load once - pass model_results
    market_prices = load_market_prices(events)      # Load once
    prices_df = get_historical_returns(market_prices)     # Load once
    
    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]
    
    # Step 2: Compute core leaderboard and events
    print("Computing core data...")
    leaderboard = get_leaderboard(positions_df, prices_df)
    # Convert Polymarket Event models to backend Event models
    
    # Step 3: Compute AgentPerformanceBackend for each model
    print("Computing agent performance data...")
    pnl_results = get_all_markets_pnls(positions_df, prices_df)
    performance = _compute_model_performance_list(model_results, leaderboard, pnl_results, positions_df, prices_df, backend_events)
    
    print("Finished computing comprehensive backend data!")
    
    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance=performance,
        model_results=model_results,
    )


def _compute_model_performance_list(
    model_results: List[ModelInvestmentDecisions],
    leaderboard: List[LeaderboardEntryBackend], 
    pnl_results: dict, 
    positions_df: pd.DataFrame, 
    prices_df: pd.DataFrame,
    backend_events: List[EventBackend]
) -> List[ModelPerformanceBackend]:
    """Compute ModelPerformanceBackend data for each model."""
    

    pass



if __name__ == "__main__":
    get_data_for_backend()