from datetime import date, datetime

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


def _build_prices_df(market_ids: list[str]) -> pd.DataFrame:
    """Create synthetic daily prices for all markets.

    Dates: 2025-08-02, 2025-08-03, 2025-08-04, 2025-08-05
    Baseline: 0.50 then 0.50; single move on 08-04 to either 0.60 (+20%) or 0.40 (-20%),
    then flat on 08-05.
    """
    dates = [
        date(2025, 8, 2),
        date(2025, 8, 3),
        date(2025, 8, 4),
        date(2025, 8, 5),
    ]

    # Define per-market move on 08-04 (relative to 0.50)
    # up = 0.60 ( +20% ); down = 0.40 ( -20% )
    market_move = {
        "event_1_market_1": 0.60,  # up
        "event_1_market_2": 0.40,  # down
        "event_2_market_1": 0.60,  # up
        "event_2_market_2": 0.60,  # up
        "event_3_market_1": 0.40,  # down
        "event_3_market_2": 0.40,  # down
    }

    data: dict[str, list[float]] = {}
    for market_id in market_ids:
        move_price = market_move[market_id]
        data[market_id] = [0.50, 0.50, move_price, move_price]

    return pd.DataFrame(data, index=dates)


def _build_model_decisions(
    model_id: str, model_name: str, target: date
) -> ModelInvestmentDecisions:
    """Create a model's decisions across 3 events with 2 markets each."""

    def make_market_decision(
        market_id: str, bet: float, odds: float = 0.5
    ) -> MarketInvestmentDecision:
        return MarketInvestmentDecision(
            market_id=market_id,
            decision=SingleInvestmentDecision(
                rationale="test", odds=odds, bet=bet, confidence=5
            ),
        )

    # Three events, two markets each
    event_1_decision = EventInvestmentDecisions(
        event_id="event_1",
        event_title="Event 1",
        market_investment_decisions=[
            make_market_decision("event_1_market_1", 1.0),
            make_market_decision("event_1_market_2", 1.0),
        ],
        unallocated_capital=0.0,
    )
    event_2_decision = EventInvestmentDecisions(
        event_id="event_2",
        event_title="Event 2",
        market_investment_decisions=[
            make_market_decision("event_2_market_1", 1.0),
            make_market_decision("event_2_market_2", 0.5),
        ],
        unallocated_capital=0.0,
    )
    event_3_decision = EventInvestmentDecisions(
        event_id="event_3",
        event_title="Event 3",
        market_investment_decisions=[
            make_market_decision("event_3_market_1", -1.0),
            make_market_decision("event_3_market_2", 1.0),
        ],
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
        event_investment_decisions=[
            event_1_decision,
            event_2_decision,
            event_3_decision,
        ],
    )


def _build_model_decisions_alt(
    model_id: str, model_name: str, target: date
) -> ModelInvestmentDecisions:
    """Second model with different bets so results differ."""

    def make_market_decision(
        market_id: str, bet: float, odds: float = 0.5
    ) -> MarketInvestmentDecision:
        return MarketInvestmentDecision(
            market_id=market_id,
            decision=SingleInvestmentDecision(
                rationale="test", odds=odds, bet=bet, confidence=5
            ),
        )

    event_1_decision = EventInvestmentDecisions(
        event_id="event_1",
        event_title="Event 1",
        market_investment_decisions=[
            make_market_decision("event_1_market_1", 0.5),
            make_market_decision("event_1_market_2", 0.5),
        ],
        unallocated_capital=0.0,
    )
    event_2_decision = EventInvestmentDecisions(
        event_id="event_2",
        event_title="Event 2",
        market_investment_decisions=[
            make_market_decision("event_2_market_1", -1.0),
            make_market_decision("event_2_market_2", -1.0),
        ],
        unallocated_capital=0.0,
    )
    event_3_decision = EventInvestmentDecisions(
        event_id="event_3",
        event_title="Event 3",
        market_investment_decisions=[
            make_market_decision("event_3_market_1", -0.5),
            make_market_decision("event_3_market_2", 0.0),
        ],
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
        event_investment_decisions=[
            event_1_decision,
            event_2_decision,
            event_3_decision,
        ],
    )


def test_compute_model_performance_end_to_end():
    # Build backend events (minimal stubs are sufficient for mapping market->event)
    backend_events = [
        EventStub(
            "event_1",
            [MarketStub("event_1_market_1"), MarketStub("event_1_market_2")],
        ),
        EventStub(
            "event_2",
            [MarketStub("event_2_market_1"), MarketStub("event_2_market_2")],
        ),
        EventStub(
            "event_3",
            [MarketStub("event_3_market_1"), MarketStub("event_3_market_2")],
        ),
    ]

    # Prices for all 6 markets
    market_ids = [
        "event_1_market_1",
        "event_1_market_2",
        "event_2_market_1",
        "event_2_market_2",
        "event_3_market_1",
        "event_3_market_2",
    ]
    prices_df = _build_prices_df(market_ids)

    # Two models, same target_date present in index (and > 2025-08-01 cutoff)
    target = date(2025, 8, 2)
    model_a_investment_decisions = _build_model_decisions("model_A", "Model A", target)
    model_b_investment_decisions = _build_model_decisions_alt(
        "model_B", "Model B", target
    )

    _, perf = _compute_model_performance(
        prices_df=prices_df,
        backend_events=backend_events,
        model_decisions=[model_a_investment_decisions, model_b_investment_decisions],
    )

    # Basic presence checks
    assert set(perf.keys()) == {"model_A", "model_B"}

    # Expected per-event returns given +20%/-20% moves on 08-04
    # Model A: event1 = 1.0*(+0.2) + 1.0*(-0.2) = 0.0
    #          event2 = 1.0*(+0.2) + 0.5*(+0.2) = 0.3
    #          event3 = (-1.0)*(-0.2) + 1.0*(-0.2) = 0.0
    #          final = average over 3 events = 0.1
    expected_a_final = 0.1

    # Model B: event1 = 0.5*(+0.2) + 0.5*(-0.2) = 0.0
    #          event2 = (-1.0)*(+0.2) + (-1.0)*(+0.2) = -0.4
    #          event3 = (-0.5)*(-0.2) + 0.0*(-0.2) = +0.1
    #          final = average over 3 events = -0.1
    expected_b_final = -0.1

    model_a_performance = perf["model_A"]
    model_b_performance = perf["model_B"]

    assert abs(model_a_performance.final_profit - expected_a_final) < 1e-9
    assert abs(model_b_performance.final_profit - expected_b_final) < 1e-9

    # Trades count: Model A has 6 non-zero bets; Model B has 5 (one zero)
    assert model_a_performance.trades_count == 6
    assert model_b_performance.trades_count == 5

    # Trades dates should contain the target date once per model
    assert model_a_performance.trades_dates == ["2025-08-02"]
    assert model_b_performance.trades_dates == ["2025-08-02"]

    # Verify per-event final pnl matches expected event returns
    def last_value(datapoints):
        return datapoints[-1].value if datapoints else None

    assert (
        abs(last_value(model_a_performance.pnl_per_event_decision["event_2"].pnl) - 0.3)
        < 1e-9
    )
    assert (
        abs(last_value(model_a_performance.pnl_per_event_decision["event_1"].pnl) - 0.0)
        < 1e-9
    )
    assert (
        abs(last_value(model_a_performance.pnl_per_event_decision["event_3"].pnl) - 0.0)
        < 1e-9
    )

    assert (
        abs(
            last_value(model_b_performance.pnl_per_event_decision["event_2"].pnl)
            - (-0.4)
        )
        < 1e-9
    )
    assert (
        abs(last_value(model_b_performance.pnl_per_event_decision["event_3"].pnl) - 0.1)
        < 1e-9
    )
    assert (
        abs(last_value(model_b_performance.pnl_per_event_decision["event_1"].pnl) - 0.0)
        < 1e-9
    )
    print("Test passed!")


if __name__ == "__main__":
    test_compute_model_performance_end_to_end()
