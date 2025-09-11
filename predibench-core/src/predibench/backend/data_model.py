from __future__ import annotations

from typing import Literal, Optional

import pandas as pd
from predibench.agent.dataclasses import ModelInvestmentDecisions
from predibench.polymarket_api import Event, Market
from pydantic import BaseModel


class TimeseriesPointBackend(BaseModel):
    date: str
    value: float

    @staticmethod
    def from_series_to_timeseries_points(
        series: pd.Series,
    ) -> list[TimeseriesPointBackend]:
        return [
            TimeseriesPointBackend(date=str(date), value=float(value))
            for date, value in series.items()
        ]


class LeaderboardEntryBackend(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    lastUpdated: str
    trend: Literal["up", "down", "stable"]
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

        return cls(**market.model_dump(exclude={"prices"}), prices=prices_backend)


class EventBackend(Event):
    """Backend-compatible event model with backend markets"""

    markets: list[MarketBackend]

    @classmethod
    def from_event(cls, event: Event) -> "EventBackend":
        """Convert core Event to backend Event"""
        return cls(
            **event.model_dump(exclude={"markets"}),
            markets=[MarketBackend.from_market(m) for m in event.markets],
        )


class EventPnlBackend(BaseModel):
    event_id: str
    pnl: list[TimeseriesPointBackend]


class MarketPnlBackend(BaseModel):
    market_id: str
    pnl: list[TimeseriesPointBackend]


class EventBrierScoreBackend(BaseModel):
    event_id: str
    brier_score: list[TimeseriesPointBackend]


class MarketBrierScoreBackend(BaseModel):
    market_id: str
    brier_score: list[TimeseriesPointBackend]


class ModelPerformanceBackend(BaseModel):
    model_name: str
    model_id: str
    final_pnl: float
    final_brier_score: float
    trades: int | None = None

    trades_dates: list[str]

    bried_scores: list[TimeseriesPointBackend]
    event_bried_scores: list[EventBrierScoreBackend]
    market_bried_scores: list[MarketBrierScoreBackend]

    cummulative_pnl: list[TimeseriesPointBackend]
    event_pnls: list[EventPnlBackend]
    market_pnls: list[MarketPnlBackend]


class FullModelResult(BaseModel):
    """Full result data for a model on a specific event"""
    model_id: str
    event_id: str
    target_date: str
    agent_type: Literal["toolcalling", "code", "deepresearch"]
    full_result_listdict: list[dict] | dict
    

class BackendData(BaseModel):
    """Comprehensive pre-computed data for all backend routes"""

    # Core data - matches API endpoints exactly
    leaderboard: list[LeaderboardEntryBackend]
    events: list[EventBackend]
    model_results: list[ModelInvestmentDecisions]
    performance_per_day: list[ModelPerformanceBackend]
    performance_per_bet: list[ModelPerformanceBackend]

    @property
    def prediction_dates(self) -> list[str]:
        """Derive unique prediction dates from model_results"""
        dates = set()
        for result in self.model_results:
            dates.add(str(result.target_date))
        return sorted(list(dates))

    @property
    def model_results_by_id(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by model_id"""
        result = {}
        for model_result in self.model_results:
            if model_result.model_id not in result:
                result[model_result.model_id] = []
            result[model_result.model_id].append(model_result)
        return result

    @property
    def model_results_by_date(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by prediction date"""
        result = {}
        for model_result in self.model_results:
            date_str = str(model_result.target_date)
            if date_str not in result:
                result[date_str] = []
            result[date_str].append(model_result)
        return result

    @property
    def model_results_by_id_and_date(
        self,
    ) -> dict[str, dict[str, ModelInvestmentDecisions]]:
        """Group model results by model_id and date"""
        result = {}
        for model_result in self.model_results:
            model_id = model_result.model_id
            date_str = str(model_result.target_date)
            if model_id not in result:
                result[model_id] = {}
            result[model_id][date_str] = model_result
        return result

    @property
    def model_results_by_event_id(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by event_id"""
        result = {}
        for model_result in self.model_results:
            for event_decision in model_result.event_investment_decisions:
                event_id = event_decision.event_id
                if event_id not in result:
                    result[event_id] = []
                result[event_id].append(model_result)
        return result

    @property
    def event_details(self) -> dict[str, EventBackend]:
        """Create event lookup dictionary"""
        return {event.id: event for event in self.events}
