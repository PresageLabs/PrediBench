from functools import lru_cache
import numpy as np
import pandas as pd
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import get_all_markets_pnls, get_positions_df
from predibench.backend.events import get_events_that_received_predictions
from predibench.backend.data_model import LeaderboardEntryBackend


def get_model_details(model_id: str) -> LeaderboardEntryBackend | dict:
    """Get detailed information for a specific model"""
    leaderboard = get_leaderboard()
    model = next((entry for entry in leaderboard if entry.id == model_id), None)

    if not model:
        return {"error": "Model not found"}

    return model


def get_model_investment_details(agent_id: str):
    """Get market-level position and PnL data for a specific model"""

    pnl_results = get_all_markets_pnls()

    # Get PnL result for this agent
    pnl_result = pnl_results[agent_id]

    # Filter for this specific agent
    positions_df = get_positions_df()
    agent_positions = positions_df[positions_df["model_name"] == agent_id]

    if agent_positions.empty:
        return {"markets": []}

    # We need to load prices separately since we no longer have the class
    from predibench.backend.pnl import get_historical_returns
    from predibench.backend.data_loader import load_market_prices
    market_prices = load_market_prices()
    prices_df = get_historical_returns(market_prices)

    # Prepare market data with questions
    markets_data = {}

    # Get market questions from events
    events = get_events_that_received_predictions()
    market_dict = {}
    for event in events:
        for market in event.markets:
            market_dict[market.id] = market

    # Process each market this agent traded
    for market_id in agent_positions["market_id"].unique():
        # Get market question
        market_question = market_dict[market_id].question

        # Get price data if available
        price_data = []
        market_prices_series = prices_df[market_id].fillna(0)
        for date_idx, price in market_prices_series.items():
            price_data.append(
                {
                    "date": date_idx.strftime("%Y-%m-%d"),
                    "price": float(price),
                }
            )

        # Get position markers, ffill positions
        market_positions = agent_positions[agent_positions["market_id"] == market_id][
            ["date", "choice"]
        ]
        market_positions = pd.concat(
            [
                market_positions,
                pd.DataFrame({"date": [market_prices_series.index[-1]], "choice": [np.nan]}),
            ]
        )  # Add a last value to allow ffill to work
        market_positions["date"] = pd.to_datetime(market_positions["date"])
        market_positions["choice"] = market_positions["choice"].astype(float)
        market_positions = market_positions.set_index("date")
        market_positions = market_positions.resample("D").ffill(limit=7).reset_index()

        position_markers = []
        for _, pos_row in market_positions.iterrows():
            position_markers.append(
                {
                    "date": pos_row["date"].strftime("%Y-%m-%d"),
                    "position": pos_row["choice"],
                }
            )

        # Get market-specific Profit
        market_pnl = pnl_result["pnl"][market_id].cumsum().fillna(0)
        pnl_data = []
        for date_idx, pnl_value in market_pnl.items():
            pnl_data.append(
                {"date": date_idx.strftime("%Y-%m-%d"), "pnl": float(pnl_value)}
            )
        markets_data[market_id] = {
            "market_id": market_id,
            "question": market_question,
            "prices": price_data,
            "positions": position_markers,
            "pnl_data": pnl_data,
        }

    return markets_data