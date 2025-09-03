import os
import json
from datetime import datetime
import threading
from cachetools import TTLCache, cached

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predibench.backend.profile import profile_time
from predibench.backend.data_model import (
    LeaderboardEntryBackend, 
    StatsBackend, 
    BackendData, 
    EventBackend, 
    MarketInvestmentDecisionBackend,
    ModelMarketDetails,
    PricePointBackend
)
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
def root():
    return {"message": "Polymarket LLM Benchmark API", "version": "1.0.0"}


########################################################
# New Routes
########################################################

@app.get("/api/leaderboard", response_model=list[LeaderboardEntryBackend])
def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return load_backend_cache().leaderboard

@app.get("/api/prediction_dates", response_model=list[str])
def get_prediction_dates_endpoint():
    return load_backend_cache().prediction_dates
    pass

@app.get("/api/model_results", response_model=list[ModelInvestmentDecisionBackend])
def get_model_results_endpoint():
    return load_backend_cache().model_results

@app.get("/api/model_results/{model_id}", response_model=list[ModelInvestmentDecisionBackend])
def get_model_results_by_id_endpoint(model_id: str):
    return load_backend_cache().model_results_by_id[model_id]

@app.get("/api/model_results/{prediction_date}", response_model=dict[str, list[PricePointBackend]])
def get_model_results_by_date_endpoint(prediction_date: str):
    return load_backend_cache().model_results_by_date[prediction_date]

@app.get("/api/model_results/{model_id}/{prediction_date}", response_model=list[ModelInvestmentDecisionBackend])
def get_model_results_by_id_and_date_endpoint(model_id: str, prediction_date: str):
    return load_backend_cache().model_results_by_id_and_date[model_id][prediction_date]

@app.get("/api/model_results/{event_id}", response_model=list[ModelInvestmentDecisionBackend])
def get_model_results_by_event_id_endpoint(event_id: str):
    return load_backend_cache().model_results_by_event_id[event_id]

@app.get("/api/pnl/{model_id}", response_model=...)
def get_pnl_endpoint(model_id: str):
    """
    For each model, the pnl (between each prediction date), the cummulative pnl is returned
    
    This data is retured accross all events, and by event
    """
    return load_backend_cache().pnl[model_id]

@app.get("/api/pnl/{model_id}/{event_id}", response_model=...)
def get_pnl_by_id_and_event_id_endpoint(model_id: str, event_id: str):
    """
    For each model, the pnl (between each prediction date), the cummulative pnl is returned
    
    This data is returned by event
    """
    return load_backend_cache().pnl_by_id_and_event_id[model_id][event_id]

@app.get("/api/events", response_model=list[EventBackend])
def get_events_endpoint(
    search: str = "",
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
):
    """Get active Polymarket events with search and filtering"""
    events = load_backend_cache().events
    return events


@app.get("/api/events/{event_id}", response_model=EventBackend)
def get_event_endpoint(event_id: str):
    """Get a specific event"""
    return load_backend_cache().event_details[event_id]



########################################################
# Old Routes
########################################################
@app.get("/api/leaderboard", response_model=list[LeaderboardEntryBackend])
def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return load_backend_cache().leaderboard


@app.get("/api/events", response_model=list[EventBackend])
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
def get_stats():
    """Get overall benchmark statistics"""
    return load_backend_cache().stats


@app.get("/api/model/{model_id}", response_model=LeaderboardEntryBackend)
def get_model_details_endpoint(model_id: str):
    """Get detailed information for a specific model"""
    data = load_backend_cache()
    if model_id not in data.model_details:
        raise HTTPException(status_code=404, detail="Model not found")
    return data.model_details[model_id]


@app.get("/api/model/{agent_id}/pnl", response_model=ModelMarketDetails)
def get_model_investment_details_endpoint(agent_id: str):
    """Get market-level position and PnL data for a specific model"""
    data = load_backend_cache()
    if agent_id not in data.model_investment_details:
        raise HTTPException(status_code=404, detail="Model investment details not found")
    return data.model_investment_details[agent_id]


@app.get("/api/event/{event_id}", response_model=EventBackend)
def get_event_details(event_id: str):
    """Get detailed information for a specific event including all its markets"""
    data = load_backend_cache()
    if event_id not in data.event_details:
        raise HTTPException(status_code=404, detail="Event not found")
    return data.event_details[event_id]


@app.get("/api/event/{event_id}/market_prices", response_model=dict[str, list[PricePointBackend]])
def get_event_market_prices_endpoint(event_id: str):
    """Get price history for all markets in an event"""
    data = load_backend_cache()
    if event_id not in data.event_market_prices:
        raise HTTPException(status_code=404, detail="Event market prices not found")
    return data.event_market_prices[event_id]


@app.get(
    "/api/event/{event_id}/investment_decisions",
    response_model=list[MarketInvestmentDecisionBackend],
)
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
