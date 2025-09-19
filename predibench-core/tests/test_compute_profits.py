import pandas as pd
from datetime import date, datetime

from predibench.agent.models import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInfo,
    ModelInvestmentDecisions,
    SingleInvestmentDecision,
)
from predibench.backend.compute_profits import _compute_profits


def create_complex_sample_data():
    """
    Create complex but predictable sample data to test all edge cases:
    - Markets that start/end at different times (with None values)
    - Multiple events per decision
    - Different events across decisions
    - Irregular betting schedule (day 1, 3, 7, 9, etc.)
    - Simple prices for easy manual verification

    Returns:
        tuple: (prices_df, model_decisions_list)
    """
    print("\n" + "="*80)
    print("CREATING COMPLEX SAMPLE DATA")
    print("="*80)

    # Create 15 days of data with irregular market activity
    dates = [date(2025, 8, i) for i in range(1, 16)]  # Aug 1-15

    # Create markets with different start/end times and simple price patterns
    prices_data = {
        # Market 1: Early starter, steady growth 0.2 → 0.8
        "market_1": [
            0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.8, 0.8,  # Days 1-9
            None, None, None, None, None, None  # Days 10-15 (market closed)
        ],

        # Market 2: Mid starter, doubles 0.3 → 0.6
        "market_2": [
            None, None, None,  # Days 1-3 (not active yet)
            0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6,  # Days 4-10
            None, None, None, None, None  # Days 11-15 (market closed)
        ],

        # Market 3: Full duration, volatile pattern
        "market_3": [
            0.5, 0.6, 0.4, 0.7, 0.3, 0.8, 0.2, 0.9, 0.1,  # Days 1-9 (volatile)
            1.0, 0.0, 1.0, 0.0, 1.0, 0.0  # Days 10-15 (extreme swings)
        ],

        # Market 4: Late starter, quick growth
        "market_4": [
            None, None, None, None, None, None,  # Days 1-6 (not active)
            0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0  # Days 7-15
        ],

        # Market 5: Very late starter, small price
        "market_5": [
            None, None, None, None, None, None, None, None,  # Days 1-8
            0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64  # Days 9-15 (exponential)
        ],

        # Market 6: Short duration market
        "market_6": [
            None, None, None, None, None, None, None, None, None,  # Days 1-9
            0.9, 0.8, 0.7, 0.6, 0.5,  # Days 10-14 (declining)
            None  # Day 15 (closed early)
        ],
    }

    # Create the prices DataFrame
    prices_df = pd.DataFrame(prices_data, index=dates)

    print("PRICE DATA STRUCTURE:")
    print("Market 1: Early start (days 1-9), steady growth 0.2 → 0.8")
    print("Market 2: Mid start (days 4-10), doubles 0.3 → 0.6")
    print("Market 3: Full duration (days 1-15), volatile pattern")
    print("Market 4: Late start (days 7-15), quick growth 0.1 → 1.0")
    print("Market 5: Very late start (days 9-15), exponential 0.01 → 0.64")
    print("Market 6: Short duration (days 10-14), declining 0.9 → 0.5")
    print(f"Price DataFrame shape: {prices_df.shape}")

    # Create model decisions with irregular schedule and varying events
    model_decisions = []

    # Decision 1: Day 1, bet on events 1, 2, 3
    decision_1 = ModelInvestmentDecisions(
        model_id="complex_test_model",
        model_info=ModelInfo(
            model_id="complex_test_model",
            model_pretty_name="Complex Test Model",
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=date(2025, 8, 1),  # Day 1
        decision_datetime=datetime.combine(date(2025, 8, 1), datetime.min.time()),
        event_investment_decisions=[
            # Event 1: Bet on markets 1 and 2
            EventInvestmentDecisions(
                event_id="event_1",
                event_title="Event 1",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_1",
                        decision=SingleInvestmentDecision(
                            rationale="Market 1 will grow from 0.2 to 0.8",
                            estimated_probability=0.7,
                            bet=0.3,  # Positive bet
                            confidence=8,
                        ),
                    ),
                    MarketInvestmentDecision(
                        market_id="market_2",
                        decision=SingleInvestmentDecision(
                            rationale="Market 2 not active yet, but will double",
                            estimated_probability=0.6,
                            bet=0.2,
                            confidence=6,
                        ),
                    ),
                ],
                unallocated_capital=0.5,
            ),
            # Event 2: Bet against market 3 (volatile)
            EventInvestmentDecisions(
                event_id="event_2",
                event_title="Event 2",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_3",
                        decision=SingleInvestmentDecision(
                            rationale="Market 3 is too volatile, betting against",
                            estimated_probability=0.3,
                            bet=-0.4,  # Negative bet
                            confidence=7,
                        ),
                    ),
                ],
                unallocated_capital=0.6,
            ),
            # Event 3: Small bet on non-existent market (edge case)
            EventInvestmentDecisions(
                event_id="event_3",
                event_title="Event 3",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_nonexistent",
                        decision=SingleInvestmentDecision(
                            rationale="This market doesn't exist in price data",
                            estimated_probability=0.5,
                            bet=0.1,
                            confidence=3,
                        ),
                    ),
                ],
                unallocated_capital=0.9,
            ),
        ],
    )

    # Decision 2: Day 3, bet on events 1, 2, 4
    decision_2 = ModelInvestmentDecisions(
        model_id="complex_test_model",
        model_info=ModelInfo(
            model_id="complex_test_model",
            model_pretty_name="Complex Test Model",
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=date(2025, 8, 3),  # Day 3
        decision_datetime=datetime.combine(date(2025, 8, 3), datetime.min.time()),
        event_investment_decisions=[
            # Event 1: Different bets on same markets
            EventInvestmentDecisions(
                event_id="event_1",
                event_title="Event 1",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_1",
                        decision=SingleInvestmentDecision(
                            rationale="Market 1 continuing to grow",
                            estimated_probability=0.8,
                            bet=0.4,
                            confidence=9,
                        ),
                    ),
                    MarketInvestmentDecision(
                        market_id="market_3",
                        decision=SingleInvestmentDecision(
                            rationale="Market 3 dropped to 0.4, might recover",
                            estimated_probability=0.6,
                            bet=0.2,
                            confidence=5,
                        ),
                    ),
                ],
                unallocated_capital=0.4,
            ),
            # Event 2: Zero bet (no trade)
            EventInvestmentDecisions(
                event_id="event_2",
                event_title="Event 2",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_2",
                        decision=SingleInvestmentDecision(
                            rationale="Neutral on market 2",
                            estimated_probability=0.5,
                            bet=0.0,  # Zero bet
                            confidence=2,
                        ),
                    ),
                ],
                unallocated_capital=1.0,
            ),
            # Event 4: Late market bet
            EventInvestmentDecisions(
                event_id="event_4",
                event_title="Event 4",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_4",
                        decision=SingleInvestmentDecision(
                            rationale="Market 4 not active yet, big potential",
                            estimated_probability=0.9,
                            bet=0.6,
                            confidence=9,
                        ),
                    ),
                ],
                unallocated_capital=0.4,
            ),
        ],
    )

    # Decision 3: Day 7, bet on events 1, 2, 5, 6
    decision_3 = ModelInvestmentDecisions(
        model_id="complex_test_model",
        model_info=ModelInfo(
            model_id="complex_test_model",
            model_pretty_name="Complex Test Model",
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=date(2025, 8, 7),  # Day 7
        decision_datetime=datetime.combine(date(2025, 8, 7), datetime.min.time()),
        event_investment_decisions=[
            # Event 1: Final bet on market 1
            EventInvestmentDecisions(
                event_id="event_1",
                event_title="Event 1",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_1",
                        decision=SingleInvestmentDecision(
                            rationale="Market 1 near peak at 0.8",
                            estimated_probability=0.8,
                            bet=0.1,  # Small final bet
                            confidence=6,
                        ),
                    ),
                ],
                unallocated_capital=0.9,
            ),
            # Event 2: Bet against volatile market 3
            EventInvestmentDecisions(
                event_id="event_2",
                event_title="Event 2",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_3",
                        decision=SingleInvestmentDecision(
                            rationale="Market 3 at 0.2, might swing up",
                            estimated_probability=0.7,
                            bet=-0.3,  # Negative bet
                            confidence=7,
                        ),
                    ),
                ],
                unallocated_capital=0.7,
            ),
            # Event 5: Exponential growth market
            EventInvestmentDecisions(
                event_id="event_5",
                event_title="Event 5",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_5",
                        decision=SingleInvestmentDecision(
                            rationale="Market 5 not active yet, exponential potential",
                            estimated_probability=0.9,
                            bet=0.5,
                            confidence=9,
                        ),
                    ),
                ],
                unallocated_capital=0.5,
            ),
            # Event 6: Short declining market
            EventInvestmentDecisions(
                event_id="event_6",
                event_title="Event 6",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_6",
                        decision=SingleInvestmentDecision(
                            rationale="Market 6 not active yet, expect decline",
                            estimated_probability=0.2,
                            bet=-0.4,  # Bet against
                            confidence=8,
                        ),
                    ),
                ],
                unallocated_capital=0.6,
            ),
        ],
    )

    # Decision 4: Day 9, final bets
    decision_4 = ModelInvestmentDecisions(
        model_id="complex_test_model",
        model_info=ModelInfo(
            model_id="complex_test_model",
            model_pretty_name="Complex Test Model",
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=date(2025, 8, 9),  # Day 9
        decision_datetime=datetime.combine(date(2025, 8, 9), datetime.min.time()),
        event_investment_decisions=[
            # Event 5: Big bet on exponential market
            EventInvestmentDecisions(
                event_id="event_5",
                event_title="Event 5",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_5",
                        decision=SingleInvestmentDecision(
                            rationale="Market 5 just started at 0.01, exponential growth expected",
                            estimated_probability=0.95,
                            bet=0.8,  # Big bet
                            confidence=10,
                        ),
                    ),
                ],
                unallocated_capital=0.2,
            ),
            # Event 6: Bet on declining market 6
            EventInvestmentDecisions(
                event_id="event_6",
                event_title="Event 6",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_6",
                        decision=SingleInvestmentDecision(
                            rationale="Market 6 will start declining from 0.9",
                            estimated_probability=0.1,
                            bet=-0.6,  # Strong negative bet
                            confidence=9,
                        ),
                    ),
                ],
                unallocated_capital=0.4,
            ),
        ],
    )

    model_decisions = [decision_1, decision_2, decision_3, decision_4]

    print("\nDECISION SCHEDULE:")
    print("Day 1: Events 1, 2, 3 (markets 1, 2, 3, nonexistent)")
    print("Day 3: Events 1, 2, 4 (markets 1, 2, 3, 4)")
    print("Day 7: Events 1, 2, 5, 6 (markets 1, 3, 5, 6)")
    print("Day 9: Events 5, 6 (markets 5, 6)")

    print(f"\nTotal decisions: {len(model_decisions)}")
    total_events = sum(len(d.event_investment_decisions) for d in model_decisions)
    print(f"Total events: {total_events}")

    print("="*80)

    return prices_df, model_decisions


def test_complex_sample_data():
    """
    Test the complex sample data creation and basic computation.
    """
    prices_df, model_decisions = create_complex_sample_data()

    # Run the computation
    print("\n" + "="*80)
    print("RUNNING COMPUTE_PROFITS ON COMPLEX DATA")
    print("="*80)

    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
        recompute_bets_with_kelly_criterion=False,
    )

    # Basic validation
    assert len(enriched_decisions) == 4, f"Expected 4 decisions, got {len(enriched_decisions)}"
    assert len(model_performances) == 1, f"Expected 1 model, got {len(model_performances)}"
    assert "complex_test_model" in model_performances, "Model ID not found in performances"

    performance = model_performances["complex_test_model"]

    print(f"Model: {performance.model_name}")
    print(f"Final profit: {performance.final_profit}")
    print(f"Trade count: {performance.trades_count}")
    print(f"Trade dates: {performance.trades_dates}")
    print(f"Final Brier score: {performance.final_brier_score}")
    print(f"Average returns: {performance.average_returns}")

    print("\nCOMPLEX DATA TEST PASSED ✓")
    return enriched_decisions, model_performances


if __name__ == "__main__":
    # Test the data creation function
    test_complex_sample_data()