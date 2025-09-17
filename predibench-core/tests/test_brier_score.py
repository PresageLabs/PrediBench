from datetime import date

import numpy as np
import pandas as pd
import pytest
from predibench.backend.brier import calculate_brier_scores


def test_brier_score_calculation():
    """Test basic Brier score calculation"""

    # Create test data
    dates = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]

    # Create positions DataFrame (agent positions over time)
    positions_df = pd.DataFrame(
        {"market_1": [1.0, 1.0, 0.0], "market_2": [0.0, 1.0, 1.0]}, index=dates
    )

    # Create prices DataFrame (market prices over time)
    prices_df = pd.DataFrame(
        {
            "market_1": [0.5, 0.7, 0.9],  # Final outcome: 0.9 (close to 1)
            "market_2": [0.6, 0.3, 0.1],  # Final outcome: 0.1 (close to 0)
        },
        index=dates,
    )

    # Create decisions DataFrame (model predictions/estimated_probability)
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.6, 0.8, 0.9],  # Predictions for market_1
            "market_2": [0.4, 0.3, 0.2],  # Predictions for market_2
        },
        index=dates,
    )

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

    positions_df = pd.DataFrame({"market_1": [1.0, 1.0]}, index=dates)

    prices_df = pd.DataFrame(
        {
            "market_1": [0.8, 1.0]  # Final outcome: 1.0
        },
        index=dates,
    )

    # Perfect predictions match the final outcome
    decisions_df = pd.DataFrame(
        {
            "market_1": [1.0, 1.0]  # Perfect predictions
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

    positions_df = pd.DataFrame({"market_1": [1.0]}, index=dates)

    prices_df = pd.DataFrame(
        {
            "market_1": [1.0]  # Final outcome: 1.0
        },
        index=dates,
    )

    # Worst prediction (opposite of outcome)
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.0]  # Predicted 0, actual was 1
        },
        index=dates,
    )

    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Worst prediction should have Brier score of 1
    expected_score = 1.0  # (0.0-1.0)^2 = 1
    assert abs(brier_result.brier_scores["market_1"].iloc[0] - expected_score) < 1e-10
    assert abs(brier_result.final_brier_score - expected_score) < 1e-10


def test_brier_score_with_missing_market_data():
    """Test Brier score calculation when some markets don't have decision data"""

    # Create test data
    dates = [date(2023, 1, 1), date(2023, 1, 2)]

    # Create positions DataFrame
    positions_df = pd.DataFrame(
        {
            "market_1": [1.0, 1.0],
            "market_2": [0.0, 1.0],
            "market_3": [1.0, 0.0],  # This market won't have decision data
        },
        index=dates,
    )

    # Create prices DataFrame (has all markets)
    prices_df = pd.DataFrame(
        {
            "market_1": [0.5, 0.9],
            "market_2": [0.6, 0.1],
            "market_3": [0.7, 0.8],  # This market won't have decision data
        },
        index=dates,
    )

    # Create decisions DataFrame (missing market_3)
    decisions_df = pd.DataFrame(
        {
            "market_1": [0.6, 0.8],
            "market_2": [0.4, 0.3],
            # market_3 is missing - this should not cause an error
        },
        index=dates,
    )

    # Create PnL calculator - this should not raise a KeyError
    brier_result = calculate_brier_scores(decisions_df, prices_df)

    # Test that Brier scores are calculated
    assert brier_result.brier_scores is not None
    assert brier_result.final_brier_score is not None

    # Test that only markets with decision data have Brier scores
    assert "market_1" in brier_result.brier_scores.columns
    assert "market_2" in brier_result.brier_scores.columns
    assert "market_3" not in brier_result.brier_scores.columns

    # Test that Brier scores are calculated correctly for existing markets
    # For market_1: final outcome = 0.9
    # Predictions: [0.6, 0.8]
    # Brier scores: [(0.6-0.9)^2, (0.8-0.9)^2] = [0.09, 0.01]
    expected_market_1_scores = [0.09, 0.01]

    np.testing.assert_array_almost_equal(
        brier_result.brier_scores["market_1"].values,
        expected_market_1_scores,
        decimal=5,
    )

    # Test that average Brier score only includes markets with data
    expected_avg = np.mean([0.09, 0.01, 0.09, 0.04])  # Only market_1 and market_2
    assert abs(brier_result.final_brier_score - expected_avg) < 1e-5


if __name__ == "__main__":
    pytest.main([__file__])
