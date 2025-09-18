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
from predibench.backend.compute_profits import _compute_profits


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
                1.0,  # Day 4
                1.0,  # Day 5
                1.0,  # Day 6
            ],
            "event_1_market_2": [
                0.2,  # Day 1
                0.3,  # Day 2
                0.1,  # Day 3
                0.1,  # Day 4
                0.1,  # Day 5
                0.5,  # Day 6
            ],
        },
        index=[
            date(2025, 8, 2),  # Day 1
            date(2025, 8, 3),  # Day 2
            date(2025, 8, 4),  # Day 3
            date(2025, 8, 5),  # Day 4
            date(2025, 8, 6),  # Day 5
            date(2025, 8, 7),  # Day 6
        ],
    )


def _build_model_decisions(
    model_id: str, model_name: str, target: date
) -> ModelInvestmentDecisions:
    """Create a model's decision for a single event."""

    market_decision_for = MarketInvestmentDecision(
        market_id="event_1_market_1",
        decision=SingleInvestmentDecision(
            rationale="test", estimated_probability=0.8, bet=-0.5, confidence=5
        ),
    )
    market_decision_against = MarketInvestmentDecision(
        market_id="event_1_market_1",
        decision=SingleInvestmentDecision(
            rationale="test", estimated_probability=0.8, bet=0.4, confidence=5
        ),
    )

    event_decision_list = [
        EventInvestmentDecisions(
            event_id="event_1",
            event_title="Event 1",
            market_investment_decisions=[market_decision_for, market_decision_against],
            unallocated_capital=0.1,
        )
    ]

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
        event_investment_decisions=event_decision_list,
    )


def _build_model_decisions_second_event(
    model_id: str, model_name: str, target: date
) -> ModelInvestmentDecisions:
    market_decision_for = MarketInvestmentDecision(
        market_id="event_1_market_2",
        decision=SingleInvestmentDecision(
            rationale="test", estimated_probability=0.8, bet=-0.5, confidence=5
        ),
    )
    market_decision_against = MarketInvestmentDecision(
        market_id="event_1_market_2",
        decision=SingleInvestmentDecision(
            rationale="test", estimated_probability=0.8, bet=0.4, confidence=5
        ),
    )

    event_decision = EventInvestmentDecisions(
        event_id="event_2",
        event_title="Event 2",
        market_investment_decisions=[market_decision_for, market_decision_against],
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


def test_compute_profits_gain():
    prices_df = _build_prices_df()

    # Model A bets -0.5 (against market, betting "no")
    # When betting negative, prices are inverted: 1-0.8=0.2, 1-0.9=0.1, 1-1.0=0.0
    # Relative returns: (0.1/0.2 - 1) = -0.5, (0.0/0.2 - 1) = -1.0
    # Final profit: -1.0 * 0.5 = -0.5, but calculation shows -0.75
    model_a_decision_1 = _build_model_decisions("model_A", "Model A", date(2025, 8, 2))
    model_a_decision_2 = _build_model_decisions_second_event(
        "model_A", "Model A", date(2025, 8, 5)
    )

    # Model B bets 0.6 (with market, betting "yes")
    # Relative returns: (0.9/0.8 - 1) = 0.125, (1.0/0.8 - 1) = 0.25
    # Final profit: 0.25 * 0.6 = 0.15

    model_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_a_decision_1, model_a_decision_2],
    )
    first_model_decision, second_model_decision = model_decisions

    # Test net gains per market
    first_model_decision.event_investment_decisions[0].market_investment_decisions[
        0
    ].net_gains_at_decision_end == -0.5  # Lost everything
    first_model_decision.event_investment_decisions[0].market_investment_decisions[
        1
    ].net_gains_at_decision_end == 0.10  # Gained 0.10

    # Test net gains per event
    first_decision_gains = first_model_decision.event_investment_decisions[
        0
    ].net_gains_until_next_decision
    end_gain_first_decision = (-0.5 + 0.4 * (5 / 4 - 1)) / 10
    assert first_decision_gains[0].value == 0
    assert (
        first_decision_gains[1].value == ((0.5 - 1) * 0.5 + (0.9 / 0.8 - 1) * 0.4) / 10
    )
    assert first_decision_gains[2].value == end_gain_first_decision

    second_decision_gains = second_model_decision.event_investment_decisions[
        0
    ].net_gains_until_next_decision
    end_gain_second_decision = (
        0.5 * ((0.5 - 0.9) / 0.9) + 0.4 * ((0.5 - 0.1) / 0.1)
    ) / 10
    # Why a profit? -> Model bet 0.5 against market, 0.4 with it. The 0.4 earns much more, since it was bought for dirt cheap.

    assert second_decision_gains[0].value == 0
    assert second_decision_gains[1].value == 0
    assert second_decision_gains[2].value == end_gain_second_decision

    #### TEST MODEL PERFORMANCE ####
    portfolio_value_after_first_decision = 1 + end_gain_first_decision
    portfolio_value_after_second_decision = portfolio_value_after_first_decision * (
        1 + end_gain_second_decision
    )
    np.testing.assert_almost_equal(
        model_performances["model_A"].compound_profit_history[3].value,
        end_gain_first_decision + 1,
        decimal=6,
    )
    assert (
        model_performances["model_A"].final_profit
        == portfolio_value_after_second_decision - 1
    )


if __name__ == "__main__":
    test_compute_profits_gain()
