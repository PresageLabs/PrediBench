import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from predibench.polymarket_api import Event
from predibench.backend.profile import profile_time
from predibench.backend.data_model import LeaderboardEntry, Stats
from predibench.backend.events import get_events_that_received_predictions, get_events_by_ids
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.market_prices import get_event_market_prices
from predibench.backend.model_details import get_model_details, get_model_investment_details
from predibench.backend.investment_decisions import get_event_investment_decisions
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

# API Endpoints
@app.get("/")
@profile_time
def root():
    return {"message": "Polymarket LLM Benchmark API", "version": "1.0.0"}


@app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
@profile_time
def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return get_leaderboard()


@app.get("/api/events", response_model=list[Event])
@profile_time
def get_events_endpoint(
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
@profile_time
def get_stats():
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
@profile_time
def get_model_details_endpoint(model_id: str):
    """Get detailed information for a specific model"""
    return get_model_details(model_id)


@app.get("/api/model/{agent_id}/pnl")
@profile_time
def get_model_investment_details_endpoint(agent_id: str):
    """Get market-level position and PnL data for a specific model"""
    return get_model_investment_details(agent_id)


@app.get("/api/event/{event_id}")
@profile_time
def get_event_details(event_id: str):
    """Get detailed information for a specific event including all its markets"""
    events_list = get_events_by_ids((event_id,))

    if not events_list:
        return {"error": "Event not found"}

    return events_list[0]


@app.get("/api/event/{event_id}/market_prices")
@profile_time
def get_event_market_prices_endpoint(event_id: str):
    """Get price history for all markets in an event"""
    return get_event_market_prices(event_id)


@app.get(
    "/api/event/{event_id}/investment_decisions",
    response_model=list[dict],
)
@profile_time
def get_event_investment_decisions_endpoint(event_id: str):
    """Get real investment choices for a specific event"""
    return get_event_investment_decisions(event_id)


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
