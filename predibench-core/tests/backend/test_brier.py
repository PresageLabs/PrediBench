from datetime import date

import numpy as np
import pandas as pd
from predibench.backend.brier import calculate_brier_scores


def test_brier_score_calculation():
    """Test basic Brier score calculation"""

    dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]

    # Create decisions DataFrame (model predictions/estimated_probability)
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.6, 0.8, 0.9],  # Predictions for market_1
            "market_2": [0.4, 0.3, 0.2],  # Predictions for market_2
        },
        index=dates,
    )

    # Create prices DataFrame (market prices over time)
    prices_df = pd.DataFrame(
        {
            "market_1": [0.5, 0.7, 0.9],  # Final outcome: 0.9 (close to 1)
            "market_2": [0.6, 0.3, 0.1],  # Final outcome: 0.1 (close to 0)
        },
        index=dates,
    )

    # Calculate Brier scores
    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Test that Brier scores are calculated
    assert brier_result.brier_scores is not None
    assert brier_result.final_brier_score is not None

    # Test Brier score values
    # For market_1: final outcome = 0.9
    # Predictions: [0.6, 0.8, 0.9]
    # Brier scores: [(0.6-0.9)^2, (0.8-0.9)^2, (0.9-0.9)^2] = [0.09, 0.01, 0.0]
    expected_market_1_scores = [0.09, 0.01, 0.0]

    # For market_2: final outcome = 0.1
    # Predictions: [0.4, 0.3, 0.2]
    # Brier scores: [(0.4-0.1)^2, (0.3-0.1)^2, (0.2-0.1)^2] = [0.09, 0.04, 0.01]
    expected_market_2_scores = [0.09, 0.04, 0.01]

    # Check market_1 Brier scores
    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values,
        expected_market_1_scores,
        decimal=5,
    )

    # Check market_2 Brier scores
    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_2"].values,
        expected_market_2_scores,
        decimal=5,
    )

    # Check average Brier score
    expected_avg = np.mean([0.09, 0.01, 0.0, 0.09, 0.04, 0.01])
    assert abs(brier_result.final_brier_score - expected_avg) < 1e-5


def test_brier_score_perfect_predictions():
    """Test Brier score with perfect predictions"""

    dates = [date(2023, 1, 1), date(2023, 1, 2)]

    # Perfect predictions match the final outcome
    decisions_df = pd.DataFrame(
        {
            "market_1": [1.0, 1.0]  # Perfect predictions
        },
        index=dates,
    )

    prices_df = pd.DataFrame(
        {
            "market_1": [0.8, 1.0]  # Final outcome: 1.0
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Perfect predictions should have Brier score of 0
    expected_scores = [0.0, 0.0]  # (1.0-1.0)^2 = 0 for both
    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values, expected_scores, decimal=5
    )

    # Average should also be 0
    assert abs(brier_result.final_brier_score) < 1e-10


def test_brier_score_worst_predictions():
    """Test Brier score with worst possible predictions"""

    dates = [date(2023, 1, 1)]

    # Worst prediction (opposite of outcome)
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.0]  # Predicted 0, actual was 1
        },
        index=dates,
    )

    prices_df = pd.DataFrame(
        {
            "market_1": [1.0]  # Final outcome: 1.0
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Worst prediction should have Brier score of 1
    expected_score = 1.0  # (0.0-1.0)^2 = 1
    assert abs(brier_result.brier_scores["market_1"].iloc[0] - expected_score) < 1e-10
    assert abs(brier_result.final_brier_score - expected_score) < 1e-10


def test_brier_score_missing_market_data():
    """Test Brier score calculation when some markets are missing from decisions"""

    dates = [date(2023, 1, 1), date(2023, 1, 2)]

    # Decisions only for market_1
    decisions_df = pd.DataFrame(
        {"market_1": [0.6, 0.8]},
        index=dates,
    )

    # Prices for both markets
    prices_df = pd.DataFrame(
        {
            "market_1": [0.5, 0.9],
            "market_2": [0.3, 0.1],  # No decisions for this market
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Should only have scores for market_1
    assert "market_1" in brier_result.brier_scores.columns
    assert "market_2" not in brier_result.brier_scores.columns

    # Check market_1 scores
    expected_scores = [(0.6 - 0.9) ** 2, (0.8 - 0.9) ** 2]  # [0.09, 0.01]
    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values,
        expected_scores,
        decimal=5,
    )

    # Check average Brier score matches expected
    expected_avg = np.mean(expected_scores)  # 0.05
    assert abs(brier_result.final_brier_score - expected_avg) < 1e-5


def test_brier_score_multiple_time_periods():
    """Test Brier score calculation with predictions over multiple time periods"""

    dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)]

    # Model predictions that get better over time
    decisions_df = pd.DataFrame(
        {
            "market_1": [
                0.3,
                0.5,
                0.7,
                0.9,
            ],  # Improving predictions toward final outcome of 1.0
            "market_2": [
                0.8,
                0.6,
                0.4,
                0.2,
            ],  # Improving predictions toward final outcome of 0.0
        },
        index=dates,
    )

    prices_df = pd.DataFrame(
        {
            "market_1": [0.4, 0.6, 0.8, 1.0],  # Final outcome: 1.0
            "market_2": [0.7, 0.5, 0.3, 0.0],  # Final outcome: 0.0
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Expected scores for market_1 (final outcome = 1.0)
    expected_market_1_scores = [
        (0.3 - 1.0) ** 2,  # 0.49
        (0.5 - 1.0) ** 2,  # 0.25
        (0.7 - 1.0) ** 2,  # 0.09
        (0.9 - 1.0) ** 2,  # 0.01
    ]

    # Expected scores for market_2 (final outcome = 0.0)
    expected_market_2_scores = [
        (0.8 - 0.0) ** 2,  # 0.64
        (0.6 - 0.0) ** 2,  # 0.36
        (0.4 - 0.0) ** 2,  # 0.16
        (0.2 - 0.0) ** 2,  # 0.04
    ]

    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values,
        expected_market_1_scores,
        decimal=5,
    )

    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_2"].values,
        expected_market_2_scores,
        decimal=5,
    )

    # Check average Brier score
    all_scores = expected_market_1_scores + expected_market_2_scores
    expected_avg = np.mean(all_scores)
    assert abs(brier_result.final_brier_score - expected_avg) < 1e-5


def test_brier_score_edge_cases():
    """Test Brier score calculation with edge case predictions (0.0 and 1.0)"""

    dates = [date(2023, 1, 1), date(2023, 1, 2)]

    # Edge case predictions: 0.0 and 1.0
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.0, 1.0],  # Worst then best prediction
            "market_2": [1.0, 0.0],  # Best then worst prediction
        },
        index=dates,
    )

    prices_df = pd.DataFrame(
        {
            "market_1": [0.5, 1.0],  # Final outcome: 1.0
            "market_2": [0.8, 0.0],  # Final outcome: 0.0
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Expected scores for market_1 (final outcome = 1.0)
    expected_market_1_scores = [
        (0.0 - 1.0) ** 2,  # 1.0 (worst possible)
        (1.0 - 1.0) ** 2,  # 0.0 (perfect)
    ]

    # Expected scores for market_2 (final outcome = 0.0)
    expected_market_2_scores = [
        (1.0 - 0.0) ** 2,  # 1.0 (worst possible)
        (0.0 - 0.0) ** 2,  # 0.0 (perfect)
    ]

    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values,
        expected_market_1_scores,
        decimal=5,
    )

    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_2"].values,
        expected_market_2_scores,
        decimal=5,
    )

    # Average should be 0.5 (average of [1.0, 0.0, 1.0, 0.0])
    expected_avg = 0.5
    assert abs(brier_result.final_brier_score - expected_avg) < 1e-5
