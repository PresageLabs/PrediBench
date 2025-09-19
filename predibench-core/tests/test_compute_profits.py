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


def calculate_manual_expectations():
    """
    Calculate all expected values manually, independent of _compute_profits code.
    This serves as ground truth to identify bugs in the actual implementation.
    """
    prices_df, model_decisions = create_complex_sample_data()

    print("\n" + "="*80)
    print("MANUAL CALCULATION OF EXPECTED VALUES")
    print("="*80)

    # Manual calculation structures
    manual_results = {
        'market_returns': {},  # individual market returns by decision/market
        'event_returns': {},   # aggregated event returns by decision/event
        'portfolio_pnl': [],   # day-by-day portfolio value
        'brier_scores': [],    # all brier score calculations
        'trade_count': 0,      # total trades executed
        'expected_final_profit': 0,
        'expected_avg_returns': {},
        'expected_brier_score': 0,
    }

    print("\n--- STEP 1: INDIVIDUAL MARKET RETURN CALCULATIONS ---")

    # Decision 1 (Day 1): Events 1, 2, 3
    print("\n** DECISION 1 (2025-08-01) **")

    # Event 1, Market 1: 0.2 (day 1) → 0.8 (day 9), bet = 0.3
    market_1_start = 0.2  # day 1 price
    market_1_end = 0.8    # final price day 9
    bet_1_1 = 0.3
    market_1_return = (market_1_end / market_1_start - 1) * bet_1_1
    print(f"Event 1, Market 1: ({market_1_end}/{market_1_start} - 1) * {bet_1_1} = {market_1_return}")
    manual_results['market_returns']['d1_e1_m1'] = market_1_return

    # Event 1, Market 2: Not active on day 1, so no return
    print("Event 1, Market 2: Not active on day 1, no return calculated")
    manual_results['market_returns']['d1_e1_m2'] = 0.0  # No trade possible

    # Event 2, Market 3: 0.5 (day 1) → 0.0 (day 15), bet = -0.4 (negative)
    # For negative bets, prices are inverted: (1-price)
    market_3_start = 0.5  # day 1 price
    market_3_end = 0.0    # final price day 15
    bet_2_3 = 0.4  # absolute value of bet
    # Inverted prices: start = 1-0.5 = 0.5, end = 1-0.0 = 1.0
    inverted_start = 1 - market_3_start  # 0.5
    inverted_end = 1 - market_3_end      # 1.0
    market_3_return = (inverted_end / inverted_start - 1) * bet_2_3
    print(f"Event 2, Market 3 (negative): inverted ({inverted_end}/{inverted_start} - 1) * {bet_2_3} = {market_3_return}")
    manual_results['market_returns']['d1_e2_m3'] = market_3_return

    # Event 3, Market nonexistent: No price data, no return
    print("Event 3, Market nonexistent: No price data, no return")
    manual_results['market_returns']['d1_e3_nonexistent'] = 0.0

    # Decision 2 (Day 3): Events 1, 2, 4
    print("\n** DECISION 2 (2025-08-03) **")

    # Event 1, Market 1: 0.4 (day 3) → 0.8 (day 9), bet = 0.4
    market_1_start_d3 = 0.4
    market_1_end_d3 = 0.8
    bet_d2_1_1 = 0.4
    market_1_return_d3 = (market_1_end_d3 / market_1_start_d3 - 1) * bet_d2_1_1
    print(f"Event 1, Market 1: ({market_1_end_d3}/{market_1_start_d3} - 1) * {bet_d2_1_1} = {market_1_return_d3}")
    manual_results['market_returns']['d3_e1_m1'] = market_1_return_d3

    # Event 1, Market 3: 0.4 (day 3) → 0.0 (day 15), bet = 0.2
    market_3_start_d3 = 0.4
    market_3_end_d3 = 0.0
    bet_d2_1_3 = 0.2
    market_3_return_d3 = (market_3_end_d3 / market_3_start_d3 - 1) * bet_d2_1_3
    print(f"Event 1, Market 3: ({market_3_end_d3}/{market_3_start_d3} - 1) * {bet_d2_1_3} = {market_3_return_d3}")
    manual_results['market_returns']['d3_e1_m3'] = market_3_return_d3

    # Event 2, Market 2: bet = 0.0, so no return
    print("Event 2, Market 2: Zero bet, no return")
    manual_results['market_returns']['d3_e2_m2'] = 0.0

    # Event 4, Market 4: Not active on day 3, no return
    print("Event 4, Market 4: Not active on day 3, no return")
    manual_results['market_returns']['d3_e4_m4'] = 0.0

    # Decision 3 (Day 7): Events 1, 2, 5, 6
    print("\n** DECISION 3 (2025-08-07) **")

    # Event 1, Market 1: 0.8 (day 7) → 0.8 (day 9), bet = 0.1
    market_1_start_d7 = 0.8
    market_1_end_d7 = 0.8
    bet_d3_1_1 = 0.1
    market_1_return_d7 = (market_1_end_d7 / market_1_start_d7 - 1) * bet_d3_1_1
    print(f"Event 1, Market 1: ({market_1_end_d7}/{market_1_start_d7} - 1) * {bet_d3_1_1} = {market_1_return_d7}")
    manual_results['market_returns']['d7_e1_m1'] = market_1_return_d7

    # Event 2, Market 3: 0.2 (day 7) → 0.0 (day 15), bet = -0.3 (negative)
    market_3_start_d7 = 0.2
    market_3_end_d7 = 0.0
    bet_d3_2_3 = 0.3
    inverted_start_d7 = 1 - market_3_start_d7  # 0.8
    inverted_end_d7 = 1 - market_3_end_d7      # 1.0
    market_3_return_d7 = (inverted_end_d7 / inverted_start_d7 - 1) * bet_d3_2_3
    print(f"Event 2, Market 3 (negative): inverted ({inverted_end_d7}/{inverted_start_d7} - 1) * {bet_d3_2_3} = {market_3_return_d7}")
    manual_results['market_returns']['d7_e2_m3'] = market_3_return_d7

    # Event 5, Market 5: Not active on day 7, no return
    print("Event 5, Market 5: Not active on day 7, no return")
    manual_results['market_returns']['d7_e5_m5'] = 0.0

    # Event 6, Market 6: Not active on day 7, no return
    print("Event 6, Market 6: Not active on day 7, no return")
    manual_results['market_returns']['d7_e6_m6'] = 0.0

    # Decision 4 (Day 9): Events 5, 6
    print("\n** DECISION 4 (2025-08-09) **")

    # Event 5, Market 5: 0.01 (day 9) → 0.64 (day 15), bet = 0.8
    market_5_start_d9 = 0.01
    market_5_end_d9 = 0.64
    bet_d4_5_5 = 0.8
    market_5_return_d9 = (market_5_end_d9 / market_5_start_d9 - 1) * bet_d4_5_5
    print(f"Event 5, Market 5: ({market_5_end_d9}/{market_5_start_d9} - 1) * {bet_d4_5_5} = {market_5_return_d9}")
    manual_results['market_returns']['d9_e5_m5'] = market_5_return_d9

    # Event 6, Market 6: Not active on day 9, no return
    print("Event 6, Market 6: Not active on day 9, no return")
    manual_results['market_returns']['d9_e6_m6'] = 0.0

    print("\n--- STEP 2: EVENT-LEVEL AGGREGATION ---")

    # Aggregate market returns within each event (sum within event)
    # Decision 1
    event_1_d1_return = manual_results['market_returns']['d1_e1_m1'] + manual_results['market_returns']['d1_e1_m2']
    event_2_d1_return = manual_results['market_returns']['d1_e2_m3']
    event_3_d1_return = manual_results['market_returns']['d1_e3_nonexistent']

    print(f"Decision 1 - Event 1 return: {manual_results['market_returns']['d1_e1_m1']} + {manual_results['market_returns']['d1_e1_m2']} = {event_1_d1_return}")
    print(f"Decision 1 - Event 2 return: {event_2_d1_return}")
    print(f"Decision 1 - Event 3 return: {event_3_d1_return}")

    manual_results['event_returns']['d1_e1'] = event_1_d1_return
    manual_results['event_returns']['d1_e2'] = event_2_d1_return
    manual_results['event_returns']['d1_e3'] = event_3_d1_return

    # Decision 2
    event_1_d2_return = manual_results['market_returns']['d3_e1_m1'] + manual_results['market_returns']['d3_e1_m3']
    event_2_d2_return = manual_results['market_returns']['d3_e2_m2']
    event_4_d2_return = manual_results['market_returns']['d3_e4_m4']

    print(f"Decision 2 - Event 1 return: {manual_results['market_returns']['d3_e1_m1']} + {manual_results['market_returns']['d3_e1_m3']} = {event_1_d2_return}")
    print(f"Decision 2 - Event 2 return: {event_2_d2_return}")
    print(f"Decision 2 - Event 4 return: {event_4_d2_return}")

    manual_results['event_returns']['d2_e1'] = event_1_d2_return
    manual_results['event_returns']['d2_e2'] = event_2_d2_return
    manual_results['event_returns']['d2_e4'] = event_4_d2_return

    # Decision 3
    event_1_d3_return = manual_results['market_returns']['d7_e1_m1']
    event_2_d3_return = manual_results['market_returns']['d7_e2_m3']
    event_5_d3_return = manual_results['market_returns']['d7_e5_m5']
    event_6_d3_return = manual_results['market_returns']['d7_e6_m6']

    print(f"Decision 3 - Event 1 return: {event_1_d3_return}")
    print(f"Decision 3 - Event 2 return: {event_2_d3_return}")
    print(f"Decision 3 - Event 5 return: {event_5_d3_return}")
    print(f"Decision 3 - Event 6 return: {event_6_d3_return}")

    manual_results['event_returns']['d3_e1'] = event_1_d3_return
    manual_results['event_returns']['d3_e2'] = event_2_d3_return
    manual_results['event_returns']['d3_e5'] = event_5_d3_return
    manual_results['event_returns']['d3_e6'] = event_6_d3_return

    # Decision 4
    event_5_d4_return = manual_results['market_returns']['d9_e5_m5']
    event_6_d4_return = manual_results['market_returns']['d9_e6_m6']

    print(f"Decision 4 - Event 5 return: {event_5_d4_return}")
    print(f"Decision 4 - Event 6 return: {event_6_d4_return}")

    manual_results['event_returns']['d4_e5'] = event_5_d4_return
    manual_results['event_returns']['d4_e6'] = event_6_d4_return

    print("\n--- STEP 3: PORTFOLIO PNL CALCULATION ---")
    print("Note: Portfolio PnL uses period-to-period returns, not all-time returns")

    # Calculate PERIOD returns for portfolio compounding
    period_returns = {}

    # Decision 1 (Day 1 to Day 3) returns
    # Market 1: (0.4/0.2 - 1) * 0.3 = 0.3
    # Market 3 inverted: (0.6/0.5 - 1) * 0.4 = 0.08
    period_returns['d1'] = {
        'market_1': 0.3,
        'market_3': 0.08,
        'total': 0.38
    }

    # Decision 2 (Day 3 to Day 7) returns
    # Market 1: (0.8/0.4 - 1) * 0.4 = 0.4
    # Market 3: (0.2/0.4 - 1) * 0.2 = -0.1
    period_returns['d2'] = {
        'market_1': 0.4,
        'market_3': -0.1,
        'total': 0.3
    }

    # Decision 3 (Day 7 to Day 9) returns
    # Market 1: (0.8/0.8 - 1) * 0.1 = 0.0
    # Market 3 inverted: (0.9/0.8 - 1) * 0.3 = 0.0375
    period_returns['d3'] = {
        'market_1': 0.0,
        'market_3': 0.0375,
        'total': 0.0375
    }

    # Decision 4 (Day 9 to end) returns
    # Market 5: (0.64/0.01 - 1) * 0.8 = 50.4
    period_returns['d4'] = {
        'market_5': 50.4,
        'total': 50.4
    }

    # The algorithm uses COMPOUNDING with period returns
    portfolio_history = [1.0]  # Day 0 (baseline)

    # Decision 1 period return
    decision_1_total = period_returns['d1']['total']
    portfolio_after_d1 = 1.0 * (1 + decision_1_total)
    portfolio_history.append(portfolio_after_d1)

    # Decision 2 period return
    decision_2_total = period_returns['d2']['total']
    portfolio_after_d2 = portfolio_after_d1 * (1 + decision_2_total)
    portfolio_history.append(portfolio_after_d2)

    # Decision 3 period return
    decision_3_total = period_returns['d3']['total']
    portfolio_after_d3 = portfolio_after_d2 * (1 + decision_3_total)
    portfolio_history.append(portfolio_after_d3)

    # Decision 4 period return
    decision_4_total = period_returns['d4']['total']
    portfolio_after_d4 = portfolio_after_d3 * (1 + decision_4_total)
    portfolio_history.append(portfolio_after_d4)

    final_portfolio_value = portfolio_after_d4
    total_profit_from_compounding = final_portfolio_value - 1.0

    print("\nCOMPOUNDING CALCULATION WITH PERIOD RETURNS:")
    print(f"Decision 1 period return: {decision_1_total:.6f}, Portfolio: 1.0 * {1 + decision_1_total:.6f} = {portfolio_after_d1:.6f}")
    print(f"Decision 2 period return: {decision_2_total:.6f}, Portfolio: {portfolio_after_d1:.6f} * {1 + decision_2_total:.6f} = {portfolio_after_d2:.6f}")
    print(f"Decision 3 period return: {decision_3_total:.6f}, Portfolio: {portfolio_after_d2:.6f} * {1 + decision_3_total:.6f} = {portfolio_after_d3:.6f}")
    print(f"Decision 4 period return: {decision_4_total:.6f}, Portfolio: {portfolio_after_d3:.6f} * {1 + decision_4_total:.6f} = {portfolio_after_d4:.6f}")
    print(f"\nExpected final portfolio value (compounded): {final_portfolio_value:.6f}")
    print(f"Expected final profit (compounded): {total_profit_from_compounding:.6f}")

    # Show breakdown of period returns
    print("\nPERIOD RETURNS BREAKDOWN:")
    for decision, returns in period_returns.items():
        print(f"{decision}: {returns}")

    # Also show all-time returns for comparison
    total_alltime_returns = sum(manual_results['event_returns'].values())
    print(f"\nAll-time returns (for metrics): {total_alltime_returns:.6f}")

    manual_results['expected_final_profit'] = total_profit_from_compounding

    print("\n--- STEP 4: BRIER SCORE CALCULATION ---")

    # Calculate Brier scores for all predictions with outcomes
    brier_calculations = []

    # Decision 1
    # Market 1: predicted 0.7, actual 0.8
    brier_d1_m1 = (0.8 - 0.7) ** 2
    brier_calculations.append(('d1_m1', 0.8, 0.7, brier_d1_m1))

    # Market 3: predicted 0.3, actual 0.0
    brier_d1_m3 = (0.0 - 0.3) ** 2
    brier_calculations.append(('d1_m3', 0.0, 0.3, brier_d1_m3))

    # Decision 2
    # Market 1: predicted 0.8, actual 0.8
    brier_d2_m1 = (0.8 - 0.8) ** 2
    brier_calculations.append(('d2_m1', 0.8, 0.8, brier_d2_m1))

    # Market 3: predicted 0.6, actual 0.0
    brier_d2_m3 = (0.0 - 0.6) ** 2
    brier_calculations.append(('d2_m3', 0.0, 0.6, brier_d2_m3))

    # Decision 3
    # Market 1: predicted 0.8, actual 0.8
    brier_d3_m1 = (0.8 - 0.8) ** 2
    brier_calculations.append(('d3_m1', 0.8, 0.8, brier_d3_m1))

    # Market 3: predicted 0.7, actual 0.0
    brier_d3_m3 = (0.0 - 0.7) ** 2
    brier_calculations.append(('d3_m3', 0.0, 0.7, brier_d3_m3))

    # Decision 4
    # Market 5: predicted 0.95, actual 0.64
    brier_d4_m5 = (0.64 - 0.95) ** 2
    brier_calculations.append(('d4_m5', 0.64, 0.95, brier_d4_m5))

    for name, actual, predicted, brier in brier_calculations:
        print(f"{name}: ({actual} - {predicted})² = {brier}")

    # Average Brier score
    all_brier_scores = [b[3] for b in brier_calculations]
    expected_brier = sum(all_brier_scores) / len(all_brier_scores)
    print(f"Expected average Brier score: {sum(all_brier_scores)} / {len(all_brier_scores)} = {expected_brier}")

    manual_results['expected_brier_score'] = expected_brier
    manual_results['brier_scores'] = brier_calculations

    print("\n--- STEP 5: TRADE COUNT ---")

    # Count non-zero bets on markets that have price data
    trades = 0
    trade_details = []

    # Decision 1
    if manual_results['market_returns']['d1_e1_m1'] != 0:  # Market 1 has data
        trades += 1
        trade_details.append('d1_m1')
    # Market 2 doesn't have data on day 1
    if manual_results['market_returns']['d1_e2_m3'] != 0:  # Market 3 has data
        trades += 1
        trade_details.append('d1_m3')
    # Nonexistent market doesn't count

    # Decision 2
    if manual_results['market_returns']['d3_e1_m1'] != 0:  # Market 1 has data
        trades += 1
        trade_details.append('d2_m1')
    if manual_results['market_returns']['d3_e1_m3'] != 0:  # Market 3 has data
        trades += 1
        trade_details.append('d2_m3')
    # Zero bet doesn't count
    # Market 4 doesn't have data on day 3

    # Decision 3
    # Market 1 on Day 7: bet = 0.1, so it's a trade even if return is 0
    trades += 1
    trade_details.append('d3_m1')
    if manual_results['market_returns']['d7_e2_m3'] != 0:  # Market 3 has data
        trades += 1
        trade_details.append('d3_m3')
    # Markets 5 and 6 don't have data on day 7

    # Decision 4
    if manual_results['market_returns']['d9_e5_m5'] != 0:  # Market 5 has data
        trades += 1
        trade_details.append('d4_m5')
    # Market 6 doesn't have data on day 9

    print(f"Expected trade count: {trades}")
    print(f"Trade details: {trade_details}")

    manual_results['trade_count'] = trades

    print("\n--- STEP 6: AVERAGE RETURNS BY TIME HORIZON ---")

    # The algorithm averages ALL event returns, including zeros
    all_event_returns = list(manual_results['event_returns'].values())

    # Calculate average including all events (even those with 0 return)
    avg_return_all = sum(all_event_returns) / len(all_event_returns) if all_event_returns else 0.0

    # Also show non-zero for comparison
    non_zero_returns = [r for r in all_event_returns if r != 0]
    avg_return_nonzero = sum(non_zero_returns) / len(non_zero_returns) if non_zero_returns else 0.0

    print(f"All event returns (including zeros): {all_event_returns}")
    print(f"Total events: {len(all_event_returns)}")
    print(f"Sum of returns: {sum(all_event_returns)}")
    print(f"Expected average return (including zeros): {sum(all_event_returns)} / {len(all_event_returns)} = {avg_return_all}")
    print(f"")
    print(f"For comparison - non-zero returns only: {non_zero_returns}")
    print(f"Average of non-zero returns: {avg_return_nonzero}")

    manual_results['expected_avg_returns'] = {
        'all_time_return': avg_return_all,
        # Other time horizons would require more detailed calculation
    }

    print("="*80)
    return manual_results


def test_manual_vs_actual_comparison():
    """
    Compare manually calculated expected values with actual _compute_profits output.
    """
    print("\n" + "="*80)
    print("COMPARING MANUAL CALCULATIONS VS ACTUAL RESULTS")
    print("="*80)

    # Get manual expectations
    manual_results = calculate_manual_expectations()

    # Get actual results
    prices_df, model_decisions = create_complex_sample_data()
    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
        recompute_bets_with_kelly_criterion=False,
    )

    actual_performance = model_performances["complex_test_model"]

    print("\n--- COMPARISON RESULTS ---")

    # Final profit comparison
    print(f"Final Profit:")
    print(f"  Manual expectation: {manual_results['expected_final_profit']:.6f}")
    print(f"  Actual result:      {actual_performance.final_profit:.6f}")
    print(f"  Difference:         {abs(actual_performance.final_profit - manual_results['expected_final_profit']):.6f}")

    # Trade count comparison
    print(f"\nTrade Count:")
    print(f"  Manual expectation: {manual_results['trade_count']}")
    print(f"  Actual result:      {actual_performance.trades_count}")
    print(f"  Match: {'✓' if manual_results['trade_count'] == actual_performance.trades_count else '✗'}")

    # Brier score comparison
    print(f"\nBrier Score:")
    print(f"  Manual expectation: {manual_results['expected_brier_score']:.6f}")
    print(f"  Actual result:      {actual_performance.final_brier_score:.6f}")
    print(f"  Difference:         {abs(actual_performance.final_brier_score - manual_results['expected_brier_score']):.6f}")

    # Average returns comparison (all-time)
    if 'all_time_return' in manual_results['expected_avg_returns']:
        print(f"\nAverage All-Time Return:")
        print(f"  Manual expectation: {manual_results['expected_avg_returns']['all_time_return']:.6f}")
        print(f"  Actual result:      {actual_performance.average_returns.all_time_return:.6f}")
        print(f"  Difference:         {abs(actual_performance.average_returns.all_time_return - manual_results['expected_avg_returns']['all_time_return']):.6f}")

    print("\n--- DETAILED MARKET RETURN ANALYSIS ---")

    # Analyze individual market returns from enriched decisions
    for i, decision in enumerate(enriched_decisions):
        print(f"\nDecision {i+1} ({decision.target_date}):")
        for event in decision.event_investment_decisions:
            print(f"  Event {event.event_id}:")
            for market in event.market_investment_decisions:
                if market.returns:
                    print(f"    Market {market.market_id}: all-time return = {market.returns.all_time_return:.6f}")
                else:
                    print(f"    Market {market.market_id}: no returns calculated")

    print("\n--- SUMMARY ---")

    # Define tolerance for numerical comparisons
    tolerance = 1e-6

    issues_found = []

    if abs(actual_performance.final_profit - manual_results['expected_final_profit']) > tolerance:
        issues_found.append("Final profit mismatch")

    if actual_performance.trades_count != manual_results['trade_count']:
        issues_found.append("Trade count mismatch")

    if abs(actual_performance.final_brier_score - manual_results['expected_brier_score']) > tolerance:
        issues_found.append("Brier score mismatch")

    if issues_found:
        print(f"🚨 ISSUES FOUND: {', '.join(issues_found)}")
        print("The _compute_profits function has numerical errors that need investigation.")
    else:
        print("✅ All calculations match expected values within tolerance!")

    print("="*80)

    # Add assertions for pytest
    assert abs(actual_performance.final_profit - manual_results['expected_final_profit']) < tolerance, \
        f"Final profit mismatch: expected {manual_results['expected_final_profit']}, got {actual_performance.final_profit}"

    assert actual_performance.trades_count == manual_results['trade_count'], \
        f"Trade count mismatch: expected {manual_results['trade_count']}, got {actual_performance.trades_count}"

    assert abs(actual_performance.final_brier_score - manual_results['expected_brier_score']) < tolerance, \
        f"Brier score mismatch: expected {manual_results['expected_brier_score']}, got {actual_performance.final_brier_score}"

    assert abs(actual_performance.average_returns.all_time_return - manual_results['expected_avg_returns']['all_time_return']) < tolerance, \
        f"Average return mismatch: expected {manual_results['expected_avg_returns']['all_time_return']}, got {actual_performance.average_returns.all_time_return}"


if __name__ == "__main__":
    # Run comprehensive manual verification
    test_manual_vs_actual_comparison()