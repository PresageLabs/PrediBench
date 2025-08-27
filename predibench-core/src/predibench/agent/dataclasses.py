from datetime import date
from typing import Any

from pydantic import BaseModel, Field

# NOTE: price ad odd of the 'yes' on any market should be equal, since normalized to 1


class SingleModelDecision(BaseModel):
    rationale: str
    odds: float = Field(
        ..., ge=0.0, le=1.0
    )  # Model's assessment of probability (0.0 to 1.0)
    bet: float = Field(
        ..., ge=-1.0, le=1.0
    )  # Model's bet on this market (-1.0 to 1.0, sums of absolute values must be 1 with bets on other markets from this event)


class MarketInvestmentDecision(BaseModel):
    market_id: str
    model_decision: SingleModelDecision
    market_question: str | None = None


class EventInvestmentDecisions(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_investment_decisions: list[
        MarketInvestmentDecision
    ]  # Multiple markets per event


class ModelInfo(BaseModel):
    model_id: str
    model_pretty_name: str
    inference_provider: str
    company_pretty_name: str
    open_weights: bool = False
    client: Any | None = None


class ModelInvestmentDecisions(BaseModel):
    model_id: str
    model_info: ModelInfo
    target_date: date
    event_investment_decisions: list[EventInvestmentDecisions]
