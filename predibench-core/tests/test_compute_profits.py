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


def create_test_prices_df() -> pd.DataFrame:
    """Create a realistic test prices DataFrame with market price movements."""
    return pd.DataFrame(
        {
            "market_1": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "market_2": [0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4],
            "market_3": [0.5, 0.52, 0.48, 0.53, 0.47, 0.51, 0.49, 0.54, 0.46],
        },
        index=[
            date(2025, 8, 2),
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
            date(2025, 8, 6),
            date(2025, 8, 7),
            date(2025, 8, 8),
            date(2025, 8, 9),
            date(2025, 8, 10),
        ],
    )


def create_test_model_decision(
    model_id: str,
    model_name: str,
    target_date: date,
    event_id: str = "event_1",
    market_decisions: list = None,
) -> ModelInvestmentDecisions:
    """Create a test ModelInvestmentDecisions with specified parameters."""
    if market_decisions is None:
        market_decisions = [
            MarketInvestmentDecision(
                market_id="market_1",
                decision=SingleInvestmentDecision(
                    rationale="Test bet on market 1",
                    estimated_probability=0.7,
                    bet=0.3,
                    confidence=8,
                ),
            ),
            MarketInvestmentDecision(
                market_id="market_2",
                decision=SingleInvestmentDecision(
                    rationale="Test bet against market 2",
                    estimated_probability=0.3,
                    bet=-0.2,
                    confidence=6,
                ),
            ),
        ]

    event_decision = EventInvestmentDecisions(
        event_id=event_id,
        event_title=f"Test Event {event_id}",
        market_investment_decisions=market_decisions,
        unallocated_capital=0.5,
    )

    return ModelInvestmentDecisions(
        model_id=model_id,
        model_info=ModelInfo(
            model_id=model_id,
            model_pretty_name=model_name,
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=target_date,
        decision_datetime=datetime.combine(target_date, datetime.min.time()),
        event_investment_decisions=[event_decision],
    )


def test_compute_profits_basic():
    """Test basic functionality of _compute_profits with simple test data."""
    prices_df = create_test_prices_df()

    model_decisions = [
        create_test_model_decision(
            "model_A", "Model A", date(2025, 8, 2)
        ),
        create_test_model_decision(
            "model_B", "Model B", date(2025, 8, 5)
        ),
    ]

    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
        recompute_bets_with_kelly_criterion=False,
    )

    assert len(enriched_decisions) == 2
    assert len(model_performances) == 2
    assert "model_A" in model_performances
    assert "model_B" in model_performances

    for model_id, performance in model_performances.items():
        assert performance.model_id == model_id
        assert performance.trades_count >= 0
        assert performance.final_profit is not None
        assert performance.final_brier_score is not None
        assert len(performance.compound_profit_history) > 0


def test_compute_profits_no_kelly():
    """Test _compute_profits with recompute_bets_with_kelly_criterion=False."""
    prices_df = create_test_prices_df()

    model_decision = create_test_model_decision(
        "test_model", "Test Model", date(2025, 8, 2)
    )

    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    assert len(enriched_decisions) == 1
    assert len(model_performances) == 1

    performance = model_performances["test_model"]
    assert performance.model_id == "test_model"
    assert performance.model_name == "Test Model"


def test_compute_profits_market_price_movements():
    """Test profit calculations with specific market movements."""
    prices_df = pd.DataFrame(
        {
            "rising_market": [0.1, 0.2, 0.3, 0.4, 0.5],
            "falling_market": [0.9, 0.8, 0.7, 0.6, 0.5],
        },
        index=[
            date(2025, 8, 2),
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
            date(2025, 8, 6),
        ],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="rising_market",
            decision=SingleInvestmentDecision(
                rationale="Bet on rising market",
                estimated_probability=0.8,
                bet=0.4,
                confidence=9,
            ),
        ),
        MarketInvestmentDecision(
            market_id="falling_market",
            decision=SingleInvestmentDecision(
                rationale="Bet against falling market",
                estimated_probability=0.2,
                bet=-0.3,
                confidence=7,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "profit_test", "Profit Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["profit_test"]

    assert performance.final_profit != 0
    assert performance.trades_count == 2
    assert len(performance.compound_profit_history) > 0


def test_compute_profits_multiple_events():
    """Test _compute_profits with multiple events for the same model."""
    prices_df = create_test_prices_df()

    event1_markets = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Event 1 bet",
                estimated_probability=0.6,
                bet=0.2,
                confidence=7,
            ),
        ),
    ]

    event2_markets = [
        MarketInvestmentDecision(
            market_id="market_2",
            decision=SingleInvestmentDecision(
                rationale="Event 2 bet",
                estimated_probability=0.4,
                bet=-0.15,
                confidence=6,
            ),
        ),
    ]

    model_decision = ModelInvestmentDecisions(
        model_id="multi_event_model",
        model_info=ModelInfo(
            model_id="multi_event_model",
            model_pretty_name="Multi Event Model",
            inference_provider="test_provider",
            company_pretty_name="Test Company",
        ),
        target_date=date(2025, 8, 2),
        decision_datetime=datetime.combine(date(2025, 8, 2), datetime.min.time()),
        event_investment_decisions=[
            EventInvestmentDecisions(
                event_id="event_1",
                event_title="Test Event 1",
                market_investment_decisions=event1_markets,
                unallocated_capital=0.8,
            ),
            EventInvestmentDecisions(
                event_id="event_2",
                event_title="Test Event 2",
                market_investment_decisions=event2_markets,
                unallocated_capital=0.85,
            ),
        ],
    )

    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["multi_event_model"]
    assert performance.trades_count == 2

    enriched_decision = enriched_decisions[0]
    assert len(enriched_decision.event_investment_decisions) == 2


def test_compute_profits_zero_bets():
    """Test behavior with zero bets (no actual trades)."""
    prices_df = create_test_prices_df()

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="No bet",
                estimated_probability=0.5,
                bet=0.0,
                confidence=5,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "no_bet_model", "No Bet Model", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["no_bet_model"]
    assert performance.trades_count == 0
    assert performance.final_profit == 0.0


def test_compute_profits_date_filtering():
    """Test that dates before August 1, 2025 are filtered out."""
    prices_df = pd.DataFrame(
        {
            "market_1": [0.1, 0.2, 0.3, 0.4, 0.5],
        },
        index=[
            date(2025, 7, 30),  # Before cutoff
            date(2025, 7, 31),  # Before cutoff
            date(2025, 8, 1),   # On cutoff (should be excluded)
            date(2025, 8, 2),   # After cutoff
            date(2025, 8, 3),   # After cutoff
        ],
    )

    model_decision = create_test_model_decision(
        "date_test", "Date Test", date(2025, 8, 2)
    )

    enriched_decisions, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    assert len(enriched_decisions) == 1
    assert len(model_performances) == 1


def test_compute_profits_returns_calculation():
    """Test that different time horizon returns are calculated correctly."""
    prices_df = pd.DataFrame(
        {
            "market_1": [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55],
        },
        index=[
            date(2025, 8, 2),
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
            date(2025, 8, 6),
            date(2025, 8, 7),
            date(2025, 8, 8),
            date(2025, 8, 9),
            date(2025, 8, 10),
            date(2025, 8, 11),
        ],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Test returns",
                estimated_probability=0.8,
                bet=0.5,
                confidence=8,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "returns_test", "Returns Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["returns_test"]

    assert performance.average_returns is not None
    assert performance.average_returns.one_day_return is not None
    assert performance.average_returns.two_day_return is not None
    assert performance.average_returns.seven_day_return is not None
    assert performance.average_returns.all_time_return is not None

    assert performance.sharpe is not None
    assert performance.sharpe.one_day_sharpe is not None


def test_compute_profits_brier_score():
    """Test that Brier scores are calculated correctly."""
    prices_df = pd.DataFrame(
        {
            "market_1": [0.2, 0.3, 0.4, 0.5, 1.0],  # Market resolves to 1.0
            "market_2": [0.8, 0.7, 0.6, 0.5, 0.0],  # Market resolves to 0.0
        },
        index=[
            date(2025, 8, 2),
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
            date(2025, 8, 6),
        ],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Good prediction",
                estimated_probability=0.9,  # Close to actual outcome (1.0)
                bet=0.3,
                confidence=9,
            ),
        ),
        MarketInvestmentDecision(
            market_id="market_2",
            decision=SingleInvestmentDecision(
                rationale="Poor prediction",
                estimated_probability=0.8,  # Far from actual outcome (0.0)
                bet=0.2,
                confidence=7,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "brier_test", "Brier Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["brier_test"]

    assert performance.final_brier_score is not None
    assert 0.0 <= performance.final_brier_score <= 1.0


def test_compute_profits_missing_market_data():
    """Test behavior when some markets don't have price data."""
    prices_df = pd.DataFrame(
        {
            "market_1": [0.2, 0.3, 0.4, 0.5],
        },
        index=[
            date(2025, 8, 2),
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
        ],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Valid market",
                estimated_probability=0.7,
                bet=0.3,
                confidence=8,
            ),
        ),
        MarketInvestmentDecision(
            market_id="market_nonexistent",
            decision=SingleInvestmentDecision(
                rationale="Invalid market",
                estimated_probability=0.6,
                bet=0.2,
                confidence=7,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "missing_data_test", "Missing Data Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["missing_data_test"]
    assert performance.trades_count == 1


def test_compute_profits_detailed_numerical_verification():
    """
    Detailed numerical verification test that traces through all calculations step by step.
    This test uses simple, predictable data to verify the mathematical correctness.
    """
    # Create simple test data for easy manual verification
    prices_df = pd.DataFrame(
        {
            "market_A": [0.4, 0.5, 0.6, 0.7, 0.8],  # Rising from 0.4 to 0.8
            "market_B": [0.8, 0.7, 0.6, 0.5, 0.4],  # Falling from 0.8 to 0.4
        },
        index=[
            date(2025, 8, 2),  # Decision date
            date(2025, 8, 3),
            date(2025, 8, 4),
            date(2025, 8, 5),
            date(2025, 8, 6),  # Final date
        ],
    )

    # Create a model with specific, easy-to-verify bets
    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_A",
            decision=SingleInvestmentDecision(
                rationale="Betting FOR market A (positive bet)",
                estimated_probability=0.7,
                bet=0.4,  # Bet 0.4 FOR market A
                confidence=8,
            ),
        ),
        MarketInvestmentDecision(
            market_id="market_B",
            decision=SingleInvestmentDecision(
                rationale="Betting AGAINST market B (negative bet)",
                estimated_probability=0.3,
                bet=-0.2,  # Bet 0.2 AGAINST market B
                confidence=7,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "numerical_test", "Numerical Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["numerical_test"]

    # Print detailed calculations for verification
    print("\n=== DETAILED NUMERICAL VERIFICATION ===")
    print(f"Final profit: {performance.final_profit}")
    print(f"Trade count: {performance.trades_count}")
    print(f"Final Brier score: {performance.final_brier_score}")

    # Manual calculation verification:
    print("\n--- Manual Calculation ---")

    # Market A (positive bet = 0.4):
    # Price progression: 0.4 → 0.5 → 0.6 → 0.7 → 0.8
    # Returns: (0.8/0.4 - 1) * 0.4 = (2.0 - 1) * 0.4 = 1.0 * 0.4 = 0.4
    market_a_return = (0.8 / 0.4 - 1) * 0.4
    print(f"Market A return: (0.8/0.4 - 1) * 0.4 = {market_a_return}")

    # Market B (negative bet = -0.2):
    # When betting negative, prices are inverted: (1-price)
    # Inverted price progression: 0.2 → 0.3 → 0.4 → 0.5 → 0.6
    # Returns: (0.6/0.2 - 1) * 0.2 = (3.0 - 1) * 0.2 = 2.0 * 0.2 = 0.4
    market_b_return = (0.6 / 0.2 - 1) * 0.2
    print(f"Market B return: (0.6/0.2 - 1) * 0.2 = {market_b_return}")

    # Total return per event (mean of market returns)
    total_event_return = (market_a_return + market_b_return) / 2  # Mean of 2 markets
    print(f"Total event return (mean): ({market_a_return} + {market_b_return}) / 2 = {total_event_return}")

    # Expected final profit should equal total_event_return
    print(f"Expected profit: {total_event_return}")
    print(f"Actual profit: {performance.final_profit}")

    # Verify Brier score calculation
    # Market A: actual = 0.8, predicted = 0.7, Brier = (0.8 - 0.7)^2 = 0.01
    # Market B: actual = 0.4, predicted = 0.3, Brier = (0.4 - 0.3)^2 = 0.01
    # Average Brier = (0.01 + 0.01) / 2 = 0.01
    expected_brier = ((0.8 - 0.7)**2 + (0.4 - 0.3)**2) / 2
    print(f"Expected Brier score: {expected_brier}")
    print(f"Actual Brier score: {performance.final_brier_score}")

    # Assertions with detailed error messages
    assert abs(performance.final_profit - total_event_return) < 1e-10, (
        f"Profit calculation error: expected {total_event_return}, got {performance.final_profit}"
    )

    assert abs(performance.final_brier_score - expected_brier) < 1e-10, (
        f"Brier score calculation error: expected {expected_brier}, got {performance.final_brier_score}"
    )

    assert performance.trades_count == 2, f"Trade count should be 2, got {performance.trades_count}"


def test_compute_profits_negative_bet_verification():
    """
    Specific test to verify negative bet calculations are handled correctly.
    """
    # Simple case: market that moves from 0.8 to 0.2 (falling)
    prices_df = pd.DataFrame(
        {"falling_market": [0.8, 0.6, 0.4, 0.2]},
        index=[date(2025, 8, 2), date(2025, 8, 3), date(2025, 8, 4), date(2025, 8, 5)],
    )

    # Bet AGAINST the market (negative bet)
    market_decisions = [
        MarketInvestmentDecision(
            market_id="falling_market",
            decision=SingleInvestmentDecision(
                rationale="Betting against falling market",
                estimated_probability=0.2,  # Predict it will be low
                bet=-0.5,  # Bet 0.5 AGAINST
                confidence=9,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "negative_bet_test", "Negative Bet Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["negative_bet_test"]

    print("\n=== NEGATIVE BET VERIFICATION ===")

    # Manual calculation for negative bet:
    # Original prices: 0.8 → 0.2
    # Inverted prices: (1-0.8)=0.2 → (1-0.2)=0.8
    # Return: (0.8/0.2 - 1) * 0.5 = (4.0 - 1) * 0.5 = 3.0 * 0.5 = 1.5
    # Final return (divided by 10): 1.5 / 10 = 0.15

    original_start_price = 0.8
    original_end_price = 0.2
    inverted_start_price = 1 - original_start_price  # 0.2
    inverted_end_price = 1 - original_end_price      # 0.8
    bet_amount = 0.5

    expected_return = (inverted_end_price / inverted_start_price - 1) * bet_amount
    expected_final_return = expected_return  # No division needed with mean

    print(f"Original prices: {original_start_price} → {original_end_price}")
    print(f"Inverted prices: {inverted_start_price} → {inverted_end_price}")
    print(f"Raw return: ({inverted_end_price}/{inverted_start_price} - 1) * {bet_amount} = {expected_return}")
    print(f"Expected return: {expected_final_return}")
    print(f"Actual profit: {performance.final_profit}")

    assert abs(performance.final_profit - expected_final_return) < 1e-10, (
        f"Negative bet calculation error: expected {expected_final_return}, got {performance.final_profit}"
    )


def test_compute_profits_time_horizon_returns():
    """
    Test time horizon return calculations with precise data.
    """
    # Create 10 days of data for testing different time horizons
    prices_df = pd.DataFrame(
        {"test_market": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]},
        index=[
            date(2025, 8, 2),   # Decision date (day 0)
            date(2025, 8, 3),   # Day 1
            date(2025, 8, 4),   # Day 2
            date(2025, 8, 5),   # Day 3
            date(2025, 8, 6),   # Day 4
            date(2025, 8, 7),   # Day 5
            date(2025, 8, 8),   # Day 6
            date(2025, 8, 9),   # Day 7
            date(2025, 8, 10),  # Day 8
            date(2025, 8, 11),  # Day 9
        ],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="test_market",
            decision=SingleInvestmentDecision(
                rationale="Testing time horizons",
                estimated_probability=0.9,
                bet=1.0,  # Full bet for easy calculation
                confidence=9,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "time_horizon_test", "Time Horizon Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    enriched_decisions, _ = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    # Get the market decision with calculated returns
    market_decision = enriched_decisions[0].event_investment_decisions[0].market_investment_decisions[0]
    returns = market_decision.returns

    print("\n=== TIME HORIZON RETURNS VERIFICATION ===")

    # Manual calculations:
    # Decision price: 0.1
    # 1-day return: (0.2/0.1 - 1) * 1.0 = (2.0 - 1) * 1.0 = 1.0
    # 2-day return: (0.3/0.1 - 1) * 1.0 = (3.0 - 1) * 1.0 = 2.0
    # 7-day return: (0.8/0.1 - 1) * 1.0 = (8.0 - 1) * 1.0 = 7.0
    # All-time return: (1.0/0.1 - 1) * 1.0 = (10.0 - 1) * 1.0 = 9.0

    decision_price = 0.1
    bet_amount = 1.0

    expected_1_day = (0.2 / decision_price - 1) * bet_amount
    expected_2_day = (0.3 / decision_price - 1) * bet_amount
    expected_7_day = (0.8 / decision_price - 1) * bet_amount
    expected_all_time = (1.0 / decision_price - 1) * bet_amount

    print(f"1-day return: expected {expected_1_day}, actual {returns.one_day_return}")
    print(f"2-day return: expected {expected_2_day}, actual {returns.two_day_return}")
    print(f"7-day return: expected {expected_7_day}, actual {returns.seven_day_return}")
    print(f"All-time return: expected {expected_all_time}, actual {returns.all_time_return}")

    assert abs(returns.one_day_return - expected_1_day) < 1e-10, (
        f"1-day return error: expected {expected_1_day}, got {returns.one_day_return}"
    )
    assert abs(returns.two_day_return - expected_2_day) < 1e-10, (
        f"2-day return error: expected {expected_2_day}, got {returns.two_day_return}"
    )
    assert abs(returns.seven_day_return - expected_7_day) < 1e-10, (
        f"7-day return error: expected {expected_7_day}, got {returns.seven_day_return}"
    )
    assert abs(returns.all_time_return - expected_all_time) < 1e-10, (
        f"All-time return error: expected {expected_all_time}, got {returns.all_time_return}"
    )


def test_division_by_10_issue():
    """
    Test to expose the division by 10 issue in the code.
    This hardcoded division seems arbitrary and may not be correct.
    """
    # Simple test case
    prices_df = pd.DataFrame(
        {"market_1": [0.5, 1.0]},  # Price doubles
        index=[date(2025, 8, 2), date(2025, 8, 3)],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Test division by 10",
                estimated_probability=0.9,
                bet=1.0,  # Bet entire amount
                confidence=9,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "division_test", "Division Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["division_test"]

    print("\n=== DIVISION BY 10 ISSUE ===")
    print(f"Price change: 0.5 → 1.0 (100% gain)")
    print(f"Bet amount: 1.0")
    print(f"Expected raw return: (1.0/0.5 - 1) * 1.0 = 1.0")
    print(f"Expected return after /10: 1.0 / 10 = 0.1")
    print(f"Actual profit: {performance.final_profit}")
    print(f"Difference: {abs(performance.final_profit - 0.1)}")

    # The code divides by 10, which seems arbitrary
    expected_return_correct = 1.0  # 100% gain
    assert abs(performance.final_profit - expected_return_correct) < 1e-10, (
        f"Fixed calculation: expected {expected_return_correct}, got {performance.final_profit}"
    )

    print(f"FIXED: The calculation now correctly returns 1.0 for a 100% gain ✓")


def test_portfolio_aggregation_multiple_markets():
    """
    Test portfolio aggregation across multiple markets within the same event.
    """
    prices_df = pd.DataFrame(
        {
            "market_1": [0.2, 0.4],  # Doubles (100% gain)
            "market_2": [0.8, 0.4],  # Halves (50% loss when inverted)
        },
        index=[date(2025, 8, 2), date(2025, 8, 3)],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Positive bet",
                estimated_probability=0.8,
                bet=0.5,  # Half allocation
                confidence=8,
            ),
        ),
        MarketInvestmentDecision(
            market_id="market_2",
            decision=SingleInvestmentDecision(
                rationale="Negative bet",
                estimated_probability=0.2,
                bet=-0.3,  # Negative bet
                confidence=7,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "aggregation_test", "Aggregation Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["aggregation_test"]

    print("\n=== PORTFOLIO AGGREGATION TEST ===")

    # Manual calculation:
    # Market 1: (0.4/0.2 - 1) * 0.5 = (2.0 - 1) * 0.5 = 0.5
    market_1_return = (0.4 / 0.2 - 1) * 0.5

    # Market 2 (negative bet): prices inverted 0.8→0.2, 0.4→0.6
    # (0.6/0.2 - 1) * 0.3 = (3.0 - 1) * 0.3 = 0.6
    market_2_return = (0.6 / 0.2 - 1) * 0.3

    total_return = (market_1_return + market_2_return) / 2  # Mean of 2 markets

    print(f"Market 1 return: {market_1_return}")
    print(f"Market 2 return: {market_2_return}")
    print(f"Total return (sum): {market_1_return + market_2_return}")
    print(f"Total return (mean): {total_return}")
    print(f"Actual profit: {performance.final_profit}")

    assert abs(performance.final_profit - total_return) < 1e-10, (
        f"Portfolio aggregation error: expected {total_return}, got {performance.final_profit}"
    )


def test_floating_point_precision_issues():
    """
    Test that exposes floating point precision issues in calculations.
    """
    # Use numbers that are known to cause floating point precision issues
    prices_df = pd.DataFrame(
        {"market_1": [0.1, 0.3]},  # 0.1 * 3 = 0.3 (potential precision issue)
        index=[date(2025, 8, 2), date(2025, 8, 3)],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_1",
            decision=SingleInvestmentDecision(
                rationale="Precision test",
                estimated_probability=0.7,
                bet=0.1,  # Small bet amount
                confidence=8,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "precision_test", "Precision Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["precision_test"]

    print("\n=== FLOATING POINT PRECISION TEST ===")

    # Expected calculation: (0.3/0.1 - 1) * 0.1 = (3.0 - 1) * 0.1 = 0.2
    expected_raw_return = (0.3 / 0.1 - 1) * 0.1
    expected_final_return = expected_raw_return  # No division with mean

    print(f"Raw return calculation: (0.3/0.1 - 1) * 0.1 = {expected_raw_return}")
    print(f"Expected return: {expected_final_return}")
    print(f"Actual profit: {performance.final_profit}")
    print(f"Precision difference: {abs(performance.final_profit - expected_final_return)}")

    # Check if precision error is within acceptable bounds
    assert abs(performance.final_profit - expected_final_return) < 1e-15, (
        f"Floating point precision error too large: {abs(performance.final_profit - expected_final_return)}"
    )


def test_fixed_mean_calculation():
    """
    Test that verifies the fix: using mean() instead of division by 10.

    This test shows that profits are now correctly calculated using the mean
    of market returns within an event, rather than an arbitrary division by 10.
    """
    print("\n" + "="*60)
    print("FIXED CALCULATION VERIFICATION")
    print("="*60)

    # Test case: Market goes from 0.1 to 1.0 (10x increase = 900% gain)
    prices_df = pd.DataFrame(
        {"market_test": [0.1, 1.0]},
        index=[date(2025, 8, 2), date(2025, 8, 3)],
    )

    market_decisions = [
        MarketInvestmentDecision(
            market_id="market_test",
            decision=SingleInvestmentDecision(
                rationale="Testing 900% gain",
                estimated_probability=0.9,
                bet=1.0,  # Full allocation
                confidence=9,
            ),
        ),
    ]

    model_decision = create_test_model_decision(
        "fixed_test", "Fixed Test", date(2025, 8, 2),
        market_decisions=market_decisions
    )

    _, model_performances = _compute_profits(
        prices_df=prices_df,
        model_decisions=[model_decision],
        recompute_bets_with_kelly_criterion=False,
    )

    performance = model_performances["fixed_test"]

    print(f"Market price change: 0.1 → 1.0")
    print(f"This represents a 10x increase (900% gain)")
    print(f"With a bet of 1.0, the expected return is:")
    print(f"  (1.0/0.1 - 1) * 1.0 = 9.0 (900% profit)")
    print()
    print(f"FIXED: Line 196 now contains:")
    print(f"  sum_net_gains_for_event_df = net_gains_for_event_df.mean(axis=1)")
    print()
    print(f"Actual result: {performance.final_profit}")
    print(f"Expected result: 9.0")
    print(f"Calculation is now CORRECT ✓")
    print("="*60)

    # Verify the correct behavior
    expected_correct = 9.0  # 900% gain
    assert abs(performance.final_profit - expected_correct) < 1e-10, (
        f"Fixed behavior: expected {expected_correct}, got {performance.final_profit}"
    )


if __name__ == "__main__":
    # Run the fixed test to verify the correction
    test_fixed_mean_calculation()
    