from __future__ import annotations

from typing import Literal, Optional

from predibench.agent.models import (
    DataPoint,
    DecisionReturns,
    DecisionSharpe,
    ModelInvestmentDecisions,
)
from predibench.polymarket_api import Event, Market
from pydantic import BaseModel


class LeaderboardEntryBackend(BaseModel):
    model_id: str
    model_name: str
    final_profit: float
    trades_count: int
    trades_dates: list[str]
    lastUpdated: str
    trend: Literal["up", "down", "stable"]
    compound_profit_history: list[DataPoint]
    cumulative_profit_history: list[DataPoint]
    average_returns: DecisionReturns
    sharpe: DecisionSharpe
    final_brier_score: float


class MarketBackend(Market):
    """Backend-compatible market model with serializable price data"""

    prices: Optional[list[DataPoint]] = None

    @classmethod
    def from_market(cls, market: Market) -> "MarketBackend":
        """Convert core Market to backend Market with serializable prices"""
        prices_backend = None
        if market.prices is not None:
            prices_backend = [
                DataPoint(date=str(date), value=float(price))
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


class EventDecisionPnlBackend(BaseModel):
    event_id: str
    pnl: list[DataPoint]


class MarketDecisionPnlBackend(BaseModel):
    market_id: str
    pnl: list[DataPoint]


class EventBrierScoreBackend(BaseModel):
    event_id: str
    brier_score: list[DataPoint]


class MarketBrierScoreBackend(BaseModel):
    market_id: str
    brier_score: list[DataPoint]


class ModelPerformanceBackend(BaseModel):
    model_name: str
    model_id: str
    trades_count: int
    trades_dates: list[str]
    compound_profit_history: list[DataPoint]
    cumulative_profit_history: list[DataPoint]
    pnl_per_event_decision: dict[str, EventDecisionPnlBackend]
    average_returns: DecisionReturns
    sharpe: DecisionSharpe
    final_profit: float
    final_brier_score: float


class FullModelResult(BaseModel):
    """Full result data for a model on a specific event"""

    model_id: str
    event_id: str
    target_date: str
    agent_type: (
        Literal["toolcalling", "code", "deepresearch"] | None
    )  # None is for old files
    full_result_listdict: list[dict] | dict


class BackendData(BaseModel):
    """Comprehensive pre-computed data for all backend routes"""

    # Core data - matches API endpoints exactly
    leaderboard: list[LeaderboardEntryBackend]
    events: list[EventBackend]
    model_decisions: list[ModelInvestmentDecisions]
    performance_per_model: dict[str, ModelPerformanceBackend]

    @property
    def prediction_dates(self) -> list[str]:
        """Derive unique prediction dates from model_results"""
        dates = set()
        for result in self.model_decisions:
            dates.add(str(result.target_date))
        return sorted(list(dates))

    @property
    def model_results_by_id(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by model_id"""
        result: dict[str, list[ModelInvestmentDecisions]] = {}
        for model_result in self.model_decisions:
            if model_result.model_id not in result:
                result[model_result.model_id] = []
            result[model_result.model_id].append(model_result)
        return result

    @property
    def model_results_by_date(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by prediction date"""
        result: dict[str, list[ModelInvestmentDecisions]] = {}
        for model_result in self.model_decisions:
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
        result: dict[str, dict[str, ModelInvestmentDecisions]] = {}
        for model_result in self.model_decisions:
            model_id = model_result.model_id
            date_str = str(model_result.target_date)
            if model_id not in result:
                result[model_id] = {}
            result[model_id][date_str] = model_result
        return result

    @property
    def model_results_by_event_id(self) -> dict[str, list[ModelInvestmentDecisions]]:
        """Group model results by event_id"""
        result: dict[str, list[ModelInvestmentDecisions]] = {}
        for model_result in self.model_decisions:
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
