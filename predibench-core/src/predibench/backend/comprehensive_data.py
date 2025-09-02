"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""
from functools import lru_cache
from typing import Dict, List
from datetime import datetime
import pandas as pd
import numpy as np

from predibench.backend.data_model import (
    BackendData, LeaderboardEntry, Event, Stats, MarketData, 
    PricePoint, PositionPoint, PnlPoint, MarketInvestmentDecision
)
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.events import get_events_that_received_predictions, get_events_by_ids
from predibench.backend.data_loader import load_investment_choices_from_google, load_saved_events, load_agent_position, load_market_prices
from predibench.backend.pnl import get_all_markets_pnls, get_historical_returns
from predibench.polymarket_api import _HistoricalTimeSeriesRequestParameters


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
    
    # Step 3: Compute stats from leaderboard
    stats = Stats(
        topFinalCumulativePnl=max(entry.final_cumulative_pnl for entry in leaderboard),
        avgPnl=sum(entry.final_cumulative_pnl for entry in leaderboard) / len(leaderboard),
        totalTrades=sum(entry.trades for entry in leaderboard),
        totalProfit=sum(entry.final_cumulative_pnl for entry in leaderboard),
    )
    
    # Step 4: Pre-compute model details (just index the leaderboard)
    print("Computing model details...")
    model_details = {entry.id: entry for entry in leaderboard}
    
    # Step 5: Pre-compute model investment details
    print("Computing model investment details...")
    pnl_results = get_all_markets_pnls(positions_df, prices_df)
    model_investment_details = {}
    
    # Create market question lookup
    market_dict = {}
    for event in events:
        for market in event.markets:
            market_dict[market.id] = market
    
    for agent_id in pnl_results.keys():
        model_investment_details[agent_id] = _compute_model_investment_details(
            agent_id, pnl_results[agent_id], positions_df, prices_df, market_dict
        )
    
    # Step 6: Pre-compute event details (just index events)
    print("Computing event details...")
    event_details = {event.id: event for event in events}
    
    # Step 7: Pre-compute event market prices
    print("Computing event market prices...")
    event_market_prices = {}
    for event in events:
        market_prices_for_event = {}
        for market in event.markets:
            clob_token_id = market.outcomes[0].clob_token_id
            price_data_raw = _HistoricalTimeSeriesRequestParameters(
                clob_token_id=clob_token_id,
            ).get_cached_token_timeseries()
            
            # Convert to PricePoint format - price_data_raw is a pandas Series
            price_points = []
            if price_data_raw is not None:
                for date_idx, price_value in price_data_raw.items():
                    price_points.append(PricePoint(
                        date=date_idx.strftime("%Y-%m-%d"),
                        price=float(price_value)
                    ))
            market_prices_for_event[market.id] = price_points
            
        event_market_prices[event.id] = market_prices_for_event
    
    # Step 8: Pre-compute event investment decisions
    print("Computing event investment decisions...")
    event_investment_decisions = {}
    
    for event in events:
        decisions = _compute_event_investment_decisions(event.id, model_results)
        event_investment_decisions[event.id] = decisions
    
    print("Finished computing comprehensive backend data!")
    
    return BackendData(
        leaderboard=leaderboard,
        events=events,
        stats=stats,
        model_details=model_details,
        model_investment_details=model_investment_details,
        event_details=event_details,
        event_market_prices=event_market_prices,
        event_investment_decisions=event_investment_decisions
    )


def _compute_model_investment_details(
    agent_id: str, 
    pnl_result: dict, 
    positions_df: pd.DataFrame, 
    prices_df: pd.DataFrame,
    market_dict: dict
) -> Dict[str, MarketData]:
    """Compute market-level investment details for a specific model."""
    
    # Filter for this specific agent
    agent_positions = positions_df[positions_df["model_name"] == agent_id]
    
    if agent_positions.empty:
        return {}
    
    markets_data = {}
    
    # Process each market this agent traded
    for market_id in agent_positions["market_id"].unique():
        if market_id not in market_dict:
            continue
            
        # Get market question
        market_question = market_dict[market_id].question
        
        # Get price data if available
        price_data = []
        if market_id in prices_df.columns:
            market_prices_series = prices_df[market_id].fillna(0)
            for date_idx, price in market_prices_series.items():
                price_data.append(PricePoint(
                    date=date_idx.strftime("%Y-%m-%d"),
                    price=float(price)
                ))
        
        # Get position markers, ffill positions
        market_positions = agent_positions[agent_positions["market_id"] == market_id][
            ["date", "choice"]
        ]
        market_positions = pd.concat([
            market_positions,
            pd.DataFrame({"date": [market_prices_series.index[-1]], "choice": [np.nan]}),
        ])
        market_positions["date"] = pd.to_datetime(market_positions["date"])
        market_positions["choice"] = market_positions["choice"].astype(float)
        
        # Handle duplicate dates by taking the last value for each date
        market_positions = market_positions.groupby("date").last().reset_index()
        market_positions = market_positions.set_index("date")
        market_positions = market_positions.resample("D").ffill(limit=7).reset_index()
        
        position_markers = []
        for _, pos_row in market_positions.iterrows():
            # Handle NaN values in position data
            position_value = pos_row["choice"]
            if pd.isna(position_value):
                position_value = 0.0
            
            position_markers.append(PositionPoint(
                date=pos_row["date"].strftime("%Y-%m-%d"),
                position=float(position_value)
            ))
        
        # Get market-specific PnL
        pnl_data = []
        if market_id in pnl_result.market_pnls:
            # market_pnls already contains cumulative PnL as List[PnlPoint]
            pnl_data = pnl_result.market_pnls[market_id]
        
        markets_data[market_id] = MarketData(
            market_id=market_id,
            question=market_question,
            prices=price_data,
            positions=position_markers,
            pnl_data=pnl_data,
        )
    
    return markets_data


def _compute_event_investment_decisions(event_id: str, model_results: list) -> List[MarketInvestmentDecision]:
    """Compute investment decisions for a specific event."""
    
    market_investments = []
    
    # Get the latest prediction for each agent for this specific event ID
    agent_latest_predictions = {}
    for model_result in model_results:
        model_name = model_result.model_info.model_pretty_name
        for event_decision in model_result.event_investment_decisions:
            if event_decision.event_id == event_id:
                # Use target_date as a proxy for "latest"
                if (
                    model_name not in agent_latest_predictions
                    or model_result.target_date
                    > agent_latest_predictions[model_name][0].target_date
                ):
                    agent_latest_predictions[model_name] = (
                        model_result,
                        event_decision,
                    )
    
    # Extract market decisions from latest predictions
    for model_result, event_decision in agent_latest_predictions.values():
        for market_decision in event_decision.market_investment_decisions:
            market_investments.append(MarketInvestmentDecision(
                market_id=market_decision.market_id,
                model_name=model_result.model_info.model_pretty_name,
                model_id=model_result.model_id,
                bet=market_decision.model_decision.bet,
                odds=market_decision.model_decision.odds,
                confidence=market_decision.model_decision.confidence,
                rationale=market_decision.model_decision.rationale,
                date=model_result.target_date,
            ))
    
    return market_investments