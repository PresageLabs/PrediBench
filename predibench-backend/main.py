import json
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from predibench.pnl import get_pnls
from predibench.polymarket_api import (
    Event,
    EventsRequestParameters,
    _HistoricalTimeSeriesRequestParameters,
)
from predibench.storage_utils import read_from_storage, get_bucket
from predibench.common import DATA_PATH
from pydantic import BaseModel

print("Successfully imported predibench modules")

app = FastAPI(title="Polymarket LLM Benchmark API", version="1.0.0")

# CORS for local development only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Configuration
AGENT_CHOICES_REPO = "Sibyllic/predibench-3"


# Data models
class DataPoint(BaseModel):
    date: str
    value: float


class LeaderboardEntry(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    profit: int
    lastUpdated: str
    trend: str
    pnl_history: list[DataPoint]


class Stats(BaseModel):
    topFinalCumulativePnl: float
    avgPnl: float
    totalTrades: int
    totalProfit: int


# Real data loading functions
@lru_cache(maxsize=1)
def load_dataset_from_google():
    # Has bucket access, load directly from GCP bucket
    all_dataframes = []
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix="")
    
    for blob in blobs:
        if blob.name.endswith('.csv') and '/' in blob.name:
            parts = blob.name.split('/')
            if len(parts) == 2:  # date/model.csv format
                try:
                    csv_content = blob.download_as_text()
                    from io import StringIO
                    df = pd.read_csv(StringIO(csv_content))
                    all_dataframes.append(df)
                except Exception as e:
                    print(f"Error reading {blob.name}: {e}")
                    continue
    
    if not all_dataframes:
        # No CSV files found in bucket, fall back to HuggingFace
        dataset = load_dataset(AGENT_CHOICES_REPO, split="train")
        return dataset.to_pandas().sort_values("date")
    
    # Combine all CSV dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    return combined_df.sort_values("date")

@lru_cache(maxsize=1)
def load_dataset_from_huggingface():
    dataset = load_dataset(AGENT_CHOICES_REPO, split="train")
    return dataset.to_pandas().sort_values("date")

@lru_cache(maxsize=1)
def load_agent_choices():
    """Load agent choices from GCP instead of HuggingFace dataset"""
    return load_dataset_from_google()


@lru_cache(maxsize=32)
def get_events_by_ids(event_ids: tuple[str, ...]) -> list[Event]:
    """Cached wrapper for EventsRequestParameters.get_events()"""
    events = []
    for event_id in event_ids:
        events_request_parameters = EventsRequestParameters(
            id=event_id,
            limit=1,
        )
        events.append(events_request_parameters.get_events()[0])
    return events


@lru_cache(maxsize=1)
def calculate_real_performance():
    """Calculate real PnL and performance metrics exactly like gradio app"""
    agent_choices_df = load_agent_choices()
    print(f"Loaded {len(agent_choices_df)} agent choices")

    agent_choices_df["timestamp_uploaded"] = pd.to_datetime(
        agent_choices_df["timestamp_uploaded"]
    )
    today_date = datetime.today()
    agent_choices_df = agent_choices_df[
        agent_choices_df["timestamp_uploaded"] < today_date
    ]
    print(f"After timestamp filter: {len(agent_choices_df)} records")

    positions = []
    for i, row in agent_choices_df.iterrows():
        for market_decision in json.loads(row["decisions_per_market"]):
            positions.append(
                {
                    "date": row["date"],
                    "market_id": market_decision["market_id"],
                    "choice": market_decision["model_decision"]["bet"],
                    "agent_name": row["agent_name"],
                }
            )
    positions_df = pd.DataFrame.from_records(positions)

    # positions_df = positions_df.pivot(index="date", columns="market_id", values="bet")

    pnl_calculators = get_pnls(
        positions_df, write_plots=False, end_date=datetime.today()
    )
    agents_performance = {}
    for agent_name, pnl_calculator in pnl_calculators.items():
        daily_pnl = pnl_calculator.portfolio_daily_pnl

        # Generate performance history from cumulative PnL
        cumulative_pnl = pnl_calculator.portfolio_cumulative_pnl
        pnl_history = []
        for date_idx, pnl_value in cumulative_pnl.items():
            pnl_history.append(
                DataPoint(date=date_idx.strftime("%Y-%m-%d"), value=float(pnl_value))
            )

        # Calculate metrics exactly like gradio
        final_pnl = float(pnl_calculator.portfolio_cumulative_pnl.iloc[-1])
        sharpe_ratio = (
            float((daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252))
            if daily_pnl.std() > 0
            else 0
        )

        agents_performance[agent_name] = {
            "agent_name": agent_name,
            "final_cumulative_pnl": final_pnl,
            "annualized_sharpe_ratio": sharpe_ratio,
            "pnl_history": pnl_history,
            "daily_cumulative_pnl": pnl_calculator.portfolio_cumulative_pnl.tolist(),
            "dates": [
                d.strftime("%Y-%m-%d")
                for d in pnl_calculator.portfolio_cumulative_pnl.index.tolist()
            ],
        }

        print(f"Agent {agent_name}: PnL={final_pnl:.3f}, Sharpe={sharpe_ratio:.3f}")

    print(f"Calculated performance for {len(agents_performance)} agents")
    return agents_performance


# Generate leaderboard from real data only
@lru_cache(maxsize=1)
def get_leaderboard() -> list[LeaderboardEntry]:
    real_performance = calculate_real_performance()

    leaderboard = []
    for i, (agent_name, metrics) in enumerate(
        sorted(
            real_performance.items(),
            key=lambda x: x[1]["final_cumulative_pnl"],
            reverse=True,
        )
    ):
        # Determine trend
        history = metrics["pnl_history"]
        if len(history) >= 2:
            recent_change = history[-1].value - history[-2].value
            trend = (
                "up"
                if recent_change > 0.1
                else "down"
                if recent_change < -0.1
                else "stable"
            )
        else:
            trend = "stable"

        entry = LeaderboardEntry(
            id=agent_name,
            model=agent_name.replace("smolagent_", "").replace("--", "/"),
            final_cumulative_pnl=metrics["final_cumulative_pnl"],
            trades=0,
            profit=0,
            lastUpdated=datetime.now().strftime("%Y-%m-%d"),
            trend=trend,
            pnl_history=metrics["pnl_history"],
        )
        leaderboard.append(entry)

    return leaderboard


@lru_cache(maxsize=1)
def get_events_that_received_predictions() -> list[Event]:
    """Get events based that models ran predictions on"""
    # Load agent choices to see what markets they've been betting on
    df = load_agent_choices()
    event_ids = tuple(df["event_id"].unique())

    return get_events_by_ids(event_ids)


# API Endpoints
@app.get("/")
async def root():
    return {"message": "Polymarket LLM Benchmark API", "version": "1.0.0"}


@app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return get_leaderboard()


@app.get("/api/events", response_model=list[Event])
async def get_events_endpoint(
    search: str = "",
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
):
    """Get active Polymarket events with search and filtering"""
    events = get_events_that_received_predictions()

    # Apply search filter
    if search:
        search_lower = search.lower()
        events = [
            event
            for event in events
            if (search_lower in event.title.lower() if event.title else False)
            or (
                search_lower in event.description.lower()
                if event.description
                else False
            )
            or (search_lower in str(event.id).lower())
        ]

    # Apply sorting
    if sort_by == "volume" and hasattr(events[0] if events else None, "volume"):
        events.sort(key=lambda x: x.volume or 0, reverse=(order == "desc"))
    elif sort_by == "date" and hasattr(events[0] if events else None, "end_datetime"):
        events.sort(
            key=lambda x: x.end_datetime or datetime.min, reverse=(order == "desc")
        )

    # Apply limit
    return events[:limit]


@app.get("/api/stats", response_model=Stats)
async def get_stats():
    """Get overall benchmark statistics"""
    leaderboard = get_leaderboard()

    return Stats(
        topFinalCumulativePnl=max(entry.final_cumulative_pnl for entry in leaderboard),
        avgPnl=sum(entry.final_cumulative_pnl for entry in leaderboard)
        / len(leaderboard),
        totalTrades=sum(entry.trades for entry in leaderboard),
        totalProfit=sum(entry.profit for entry in leaderboard),
    )


@app.get("/api/model/{model_id}", response_model=LeaderboardEntry)
async def get_model_details(model_id: str):
    """Get detailed information for a specific model"""
    leaderboard = get_leaderboard()
    model = next((entry for entry in leaderboard if entry.id == model_id), None)

    if not model:
        return {"error": "Model not found"}

    return model


@lru_cache(maxsize=1)
def get_positions_df():
    # Calculate market-level data
    agent_choices_df = load_agent_choices()
    agent_choices_df["timestamp_uploaded"] = pd.to_datetime(
        agent_choices_df["timestamp_uploaded"]
    )
    today_date = datetime.today()
    agent_choices_df = agent_choices_df[
        agent_choices_df["timestamp_uploaded"] < today_date
    ]

    positions = []
    for i, row in agent_choices_df.iterrows():
        for market_decision in json.loads(row["decisions_per_market"]):
            positions.append(
                {
                    "date": row["date"],
                    "market_id": market_decision["market_id"],
                    "choice": market_decision["model_decision"]["bet"],
                    "agent_name": row["agent_name"],
                }
            )
    return pd.DataFrame.from_records(positions)


@lru_cache(maxsize=1)
def get_all_markets_pnls():
    positions_df = get_positions_df()
    pnl_calculators = get_pnls(
        positions_df, write_plots=False, end_date=datetime.today()
    )
    return pnl_calculators


@lru_cache(maxsize=16)
@app.get("/api/model/{agent_id}/pnl")
async def get_model_investment_details(agent_id: str):
    """Get market-level position and PnL data for a specific model"""

    pnl_calculators = get_all_markets_pnls()

    # Get PnL calculator for this agent
    pnl_calculator = pnl_calculators[agent_id]

    # Filter for this specific agent
    positions_df = get_positions_df()
    agent_positions = positions_df[positions_df["agent_name"] == agent_id]

    if agent_positions.empty:
        return {"markets": []}

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
        market_prices = pnl_calculator.prices[market_id].fillna(0)
        for date_idx, price in market_prices.items():
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
                pd.DataFrame({"date": [market_prices.index[-1]], "choice": [np.nan]}),
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

        # Get market-specific PnL
        market_pnl = pnl_calculator.pnl[market_id].cumsum().fillna(0)
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


@app.get("/api/event/{event_id}")
async def get_event_details(event_id: str):
    """Get detailed information for a specific event including all its markets"""
    events_list = get_events_by_ids((event_id,))

    if not events_list:
        return {"error": "Event not found"}

    return events_list[0]


@app.get("/api/event/{event_id}/market_prices")
async def get_event_market_prices(event_id: str):
    """Get price history for all markets in an event"""
    events_list = get_events_by_ids((event_id,))

    if not events_list:
        return {}

    event = events_list[0]
    market_prices = {}

    # Get prices for each market in the event
    for market in event.markets:
        clob_token_id = market.outcomes[0].clob_token_id
        price_data = _HistoricalTimeSeriesRequestParameters(
            clob_token_id=clob_token_id,
        ).get_token_daily_timeseries()

        market_prices[market.id] = price_data

    return market_prices


@app.get(
    "/api/event/{event_id}/investment_decisions",
    response_model=list[dict],
)
async def get_event_investment_decisions(event_id: str):
    """Get real investment choices for a specific event"""
    # Load agent choices data like in gradio app
    df = load_agent_choices()
    df["timestamp_uploaded"] = pd.to_datetime(df["timestamp_uploaded"])

    # Look for the latest prediction for each agent for this specific event ID
    event_predictions = (
        df.loc[df["event_id"] == event_id].groupby("agent_name").tail(1).copy()
    )

    # Process predictions and extract market decisions
    market_investments = []

    for _, row in event_predictions.iterrows():
        # Parse the decisions_per_market JSON
        decisions = json.loads(row["decisions_per_market"])

        for market_decision in decisions:
            market_id = market_decision["market_id"]
            model_decision = market_decision["model_decision"]

            # Create market investment result
            market_investments.append(
                {
                    "market_id": market_id,
                    "agent_name": row["agent_name"],
                    "bet": model_decision["bet"],
                    "odds": model_decision["odds"],
                    "rationale": model_decision["rationale"],
                    "date": row["date"],
                }
            )
    return market_investments


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
