import os
import json
from datetime import datetime
import threading
from cachetools import TTLCache, cached

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predibench.backend.profile import profile_time
from predibench.backend.data_model import LeaderboardEntryBackend, StatsBackend, BackendData, EventBackend
from predibench.storage_utils import read_from_storage
from predibench.common import DATA_PATH

print("Successfully imported predibench modules")

CACHE_TTL_SECONDS = 3600
_backend_cache = TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)
_cache_lock = threading.RLock()

# Load cached backend data with TTL invalidation
@cached(cache=_backend_cache, lock=_cache_lock)
def load_backend_cache() -> BackendData:
    """Load pre-computed backend data from cache (TTL-controlled)."""
    cache_file_path = DATA_PATH / "backend_cache.json"
    json_content = read_from_storage(cache_file_path)
    cached_data = json.loads(json_content)
    return BackendData.model_validate(cached_data)

# Warm cache at startup (and print status)
_initial_data = load_backend_cache()
print(f"✅ Loaded backend cache with {len(_initial_data.leaderboard)} leaderboard entries (TTL={CACHE_TTL_SECONDS}s)")




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


@app.get("/api/leaderboard", response_model=list[LeaderboardEntryBackend])
@profile_time
def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return load_backend_cache().leaderboard


@app.get("/api/events", response_model=list[EventBackend])
@profile_time
def get_events_endpoint(
    search: str = "",
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
):
    """Get active Polymarket events with search and filtering"""
    events = load_backend_cache().events

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


@app.get("/api/stats", response_model=StatsBackend)
@profile_time
def get_stats():
    """Get overall benchmark statistics"""
    return load_backend_cache().stats


@app.get("/api/model/{model_id}", response_model=LeaderboardEntryBackend)
@profile_time
def get_model_details_endpoint(model_id: str):
    """Get detailed information for a specific model"""
    data = load_backend_cache()
    if model_id not in data.model_details:
        raise HTTPException(status_code=404, detail="Model not found")
    return data.model_details[model_id]


@app.get("/api/model/{agent_id}/pnl")
@profile_time
def get_model_investment_details_endpoint(agent_id: str):
    """Get market-level position and PnL data for a specific model"""
    data = load_backend_cache()
    if agent_id not in data.model_investment_details:
        raise HTTPException(status_code=404, detail="Model investment details not found")
    return data.model_investment_details[agent_id]


@app.get("/api/event/{event_id}")
@profile_time
def get_event_details(event_id: str):
    """Get detailed information for a specific event including all its markets"""
    data = load_backend_cache()
    if event_id not in data.event_details:
        raise HTTPException(status_code=404, detail="Event not found")
    return data.event_details[event_id]


@app.get("/api/event/{event_id}/market_prices")
@profile_time
def get_event_market_prices_endpoint(event_id: str):
    """Get price history for all markets in an event"""
    data = load_backend_cache()
    if event_id not in data.event_market_prices:
        raise HTTPException(status_code=404, detail="Event market prices not found")
    return data.event_market_prices[event_id]


@app.get(
    "/api/event/{event_id}/investment_decisions",
    response_model=list[dict],
)
@profile_time
def get_event_investment_decisions_endpoint(event_id: str):
    """Get real investment choices for a specific event"""
    data = load_backend_cache()
    if event_id not in data.event_investment_decisions:
        raise HTTPException(status_code=404, detail="Event investment decisions not found")
    return data.event_investment_decisions[event_id]


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

    # ce que j'ai besoin:
    # - récupérer les résultats par model_id, et par event_id