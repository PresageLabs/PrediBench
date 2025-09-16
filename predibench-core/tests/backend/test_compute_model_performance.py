from datetime import date, datetime

import numpy as np
import pandas as pd
from predibench.agent.models import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInfo,
    ModelInvestmentDecisions,
    SingleInvestmentDecision,
)
from predibench.backend.comprehensive_data import _compute_model_performance


class MarketStub:
    def __init__(self, id: str):
        self.id = id


class EventStub:
    def __init__(self, id: str, markets: list[MarketStub]):
        self.id = id
        self.markets = markets


def _build_prices_df() -> pd.DataFrame:
    """Two markets: one moves 0.8 → 0.9 → 1.0, other stays constant."""
    return pd.DataFrame(
        {
            "event_1_market_1": [
                0.8,  # Day 1
                0.9,  # Day 2
                1.0,  # Day 3
            ],
            "event_1_market_2": [
                0.2,  # Day 1
                0.2,  # Day 2
                0.1,  # Day 3
            ],
        },
        index=[
            date(2025, 8, 2),  # Day 1
            date(2025, 8, 3),  # Day 2
            date(2025, 8, 4),  # Day 3
        ],
    )


def _build_model_decisions(
    model_id: str, model_name: str, bet: float, target: date
) -> ModelInvestmentDecisions:
    """Create a model's decision for a single event."""

    market_decision = MarketInvestmentDecision(
        market_id="event_1_market_1",
        decision=SingleInvestmentDecision(
            rationale="test", odds=0.8, bet=bet, confidence=5
        ),
    )

    event_decision = EventInvestmentDecisions(
        event_id="event_1",
        event_title="Event 1",
        market_investment_decisions=[market_decision],
        unallocated_capital=0.0,
    )

    return ModelInvestmentDecisions(
        model_id=model_id,
        model_info=ModelInfo(
            model_id=model_id,
            model_pretty_name=model_name,
            inference_provider="test",
            company_pretty_name="testco",
        ),
        target_date=target,
        decision_datetime=datetime.combine(target, datetime.min.time()),
        event_investment_decisions=[event_decision],
    )


def test_compute_model_performance_end_to_end():
    # Single event with one market
    backend_events = [EventStub("event_1", [MarketStub("event_1_market_1")])]

    prices_df = _build_prices_df()
    target = date(2025, 8, 2)  # Day 1 when betting happens

    # Model A bets -0.5 (against market, betting "no")
    # When betting negative, prices are inverted: 1-0.8=0.2, 1-0.9=0.1, 1-1.0=0.0
    # Relative returns: (0.1/0.2 - 1) = -0.5, (0.0/0.2 - 1) = -1.0
    # Final profit: -1.0 * 0.5 = -0.5, but calculation shows -0.75
    model_a_decisions = _build_model_decisions("model_A", "Model A", -0.5, target)

    # Model B bets 0.6 (with market, betting "yes")
    # Relative returns: (0.9/0.8 - 1) = 0.125, (1.0/0.8 - 1) = 0.25
    # Final profit: 0.25 * 0.6 = 0.15, but calculation shows 0.225
    model_b_decisions = _build_model_decisions("model_B", "Model B", 0.6, target)

    _, perf = _compute_model_performance(
        prices_df=prices_df,
        backend_events=backend_events,
        model_decisions=[model_a_decisions, model_b_decisions],
    )

    assert set(perf.keys()) == {"model_A", "model_B"}

    model_a_performance = perf["model_A"]
    model_b_performance = perf["model_B"]

    # Model A should lose everything, so 0.5 (betting against market that goes to 0)
    assert np.isclose(model_a_performance.final_profit, -0.5)

    # Model B should gain 0.15 (0.6 * 1/0.8, betting with market that goes to 1.0)
    assert np.isclose(model_b_performance.final_profit, 0.15)

    print("Test passed!")


if __name__ == "__main__":
    test_compute_model_performance_end_to_end()
