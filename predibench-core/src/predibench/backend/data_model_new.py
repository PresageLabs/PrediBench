from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Literal
import pandas as pd
from datetime import datetime

from predibench.polymarket_api import Market, Event


class TimeseriesPointBackend(BaseModel):
    date: str
    value: float
    
    @staticmethod
    def from_series_to_timeseries_points(series: pd.Series) -> list[TimeseriesPointBackend]:
        return [TimeseriesPointBackend(date=str(date), value=float(value)) for date, value in series.items()]

class LeaderboardEntryBackend(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    lastUpdated: str
    trend: Literal['up', 'down', 'stable']
    pnl_history: list[TimeseriesPointBackend]
    avg_brier_score: float

class MarketBackend(Market):
    """Backend-compatible market model with serializable price data"""
    prices: Optional[list[TimeseriesPointBackend]] = None

    @classmethod
    def from_market(cls, market: Market) -> "MarketBackend":
        """Convert core Market to backend Market with serializable prices"""
        prices_backend = None
        if market.prices is not None:
            prices_backend = [
                TimeseriesPointBackend(date=str(date), value=float(price))
                for date, price in market.prices.items()
            ]
        
        return cls(
            **market.model_dump(exclude={"prices"}),
            prices=prices_backend
        )

class EventBackend(Event):
    """Backend-compatible event model with backend markets"""
    markets: list[MarketBackend]
    
    @classmethod
    def from_event(cls, event: Event) -> "EventBackend":
        """Convert core Event to backend Event"""
        return cls(
            **event.model_dump(exclude={"markets"}),
            markets=[MarketBackend.from_market(m) for m in event.markets]
        )


class AgentPerformanceBackend(BaseModel):
    model_name: str
    final_pnl: float
    final_brier_score: float
    
    trades_dates: list[str]
    
    bried_scores: list[TimeseriesPointBackend]
    event_bried_scores: dict[str, list[TimeseriesPointBackend]]
    market_bried_scores: dict[str, list[TimeseriesPointBackend]]
    
    cummulative_pnl: list[TimeseriesPointBackend]
    event_pnls: dict[str, list[TimeseriesPointBackend]]
    market_pnls: dict[str, list[TimeseriesPointBackend]]


class BackendData(BaseModel):
    """Comprehensive pre-computed data for all backend routes"""
    # Core data - matches API endpoints exactly
    leaderboard: list[LeaderboardEntryBackend]
    events: list[EventBackend]
    performance: list[AgentPerformanceBackend]
