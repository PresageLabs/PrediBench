import pandas as pd
from datetime import date

from predibench.backend.brier import calculate_brier_scores


def test_calculate_brier_scores():
    """
    Test Brier score calculation with realistic prediction data.
    
    Scenario:
    - 7 days of prediction data for 3 markets
    - Agent makes predictions with varying confidence over time
    - Markets resolve with different outcomes (0.0, 1.0, 0.0)
    - Some predictions missing (NaN values)
    
    Expected behavior:
    - Brier score = (prediction - outcome)^2 for each prediction
    - Average across all non-NaN predictions
    - Markets with no predictions are dropped
    """
    # 7 days of data
    dates = [date(2024, 1, i) for i in range(1, 8)]
    
    # Agent predictions over time (probabilities between 0 and 1)
    decisions_df = pd.DataFrame({
        'market_A': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],  # Increasing confidence, market resolves to 1.0
        'market_B': [0.8, 0.7, 0.6, None, 0.4, 0.3, 0.2],  # Decreasing confidence, market resolves to 0.0
        'market_C': [0.5, None, 0.5, 0.5, None, 0.5, 0.5],  # Neutral predictions, market resolves to 0.0
        'market_D': [None, None, None, None, None, None, None]  # No predictions, should be dropped
    }, index=dates)
    
    # Market prices over time, with final resolution prices
    prices_df = pd.DataFrame({
        'market_A': [0.25, 0.35, 0.45, 0.55, 0.65, 0.80, 1.0],  # Resolves to 1.0 (YES)
        'market_B': [0.75, 0.65, 0.55, 0.45, 0.35, 0.20, 0.0],  # Resolves to 0.0 (NO)
        'market_C': [0.50, 0.48, 0.52, 0.50, 0.48, 0.25, 0.0],  # Resolves to 0.0 (NO)
        'market_D': [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 1.0]   # Has prices but no predictions
    }, index=dates)
    
    result = calculate_brier_scores(decisions_df, prices_df)
    
    # Manual calculation of expected Brier scores:
    # market_A (outcome = 1.0):
    # Day 1: (0.3 - 1.0)� = 0.49
    # Day 2: (0.4 - 1.0)� = 0.36
    # Day 3: (0.5 - 1.0)� = 0.25
    # Day 4: (0.6 - 1.0)� = 0.16
    # Day 5: (0.7 - 1.0)� = 0.09
    # Day 6: (0.8 - 1.0)� = 0.04
    # Day 7: (0.9 - 1.0)� = 0.01
    # Average for market_A = (0.49 + 0.36 + 0.25 + 0.16 + 0.09 + 0.04 + 0.01) / 7 = 1.40 / 7 = 0.2
    
    # market_B (outcome = 0.0):
    # Day 1: (0.8 - 0.0)� = 0.64
    # Day 2: (0.7 - 0.0)� = 0.49
    # Day 3: (0.6 - 0.0)� = 0.36
    # Day 4: NaN (skipped)
    # Day 5: (0.4 - 0.0)� = 0.16
    # Day 6: (0.3 - 0.0)� = 0.09
    # Day 7: (0.2 - 0.0)� = 0.04
    # Average for market_B = (0.64 + 0.49 + 0.36 + 0.16 + 0.09 + 0.04) / 6 = 1.78 / 6 = 0.2967
    
    # market_C (outcome = 0.0):
    # Day 1: (0.5 - 0.0)� = 0.25
    # Day 2: NaN (skipped)
    # Day 3: (0.5 - 0.0)� = 0.25
    # Day 4: (0.5 - 0.0)� = 0.25
    # Day 5: NaN (skipped)
    # Day 6: (0.5 - 0.0)� = 0.25
    # Day 7: (0.5 - 0.0)� = 0.25
    # Average for market_C = (0.25 + 0.25 + 0.25 + 0.25 + 0.25) / 5 = 1.25 / 5 = 0.25
    
    # Overall average calculation:
    # Total valid predictions: 7 (market_A) + 6 (market_B) + 5 (market_C) = 18
    # Sum of all Brier scores: 1.4 + 1.78 + 1.25 = 4.43
    # Average = 4.43 / 18 ≈ 0.2461
    # But pandas mean() calculates per-market average first, then averages those:
    # (0.2 + 0.2967 + 0.25) / 3 = 0.7467 / 3 ≈ 0.2489
    
    expected_avg_brier = (0.2 + (1.78/6) + 0.25) / 3
    
    # Check that market_D (no predictions) was dropped
    assert 'market_D' not in result.brier_scores.columns
    
    # Check the average Brier score
    assert abs(result.avg_brier_score - expected_avg_brier) < 0.001
    
    # Check individual market calculations
    market_a_scores = result.brier_scores['market_A']
    expected_a_scores = [(0.3 - 1.0)**2, (0.4 - 1.0)**2, (0.5 - 1.0)**2, 
                        (0.6 - 1.0)**2, (0.7 - 1.0)**2, (0.8 - 1.0)**2, (0.9 - 1.0)**2]
    
    for i, expected_score in enumerate(expected_a_scores):
        assert abs(market_a_scores.iloc[i] - expected_score) < 0.001
    
    # Verify that NaN predictions result in NaN Brier scores
    market_b_scores = result.brier_scores['market_B']
    assert pd.isna(market_b_scores.iloc[3])  # Day 4 should be NaN
    
    # Verify non-NaN values are correct
    assert abs(market_b_scores.iloc[0] - (0.8 - 0.0)**2) < 0.001
    assert abs(market_b_scores.iloc[4] - (0.4 - 0.0)**2) < 0.001
    
    print(f"Test passed: Average Brier Score = {result.avg_brier_score:.4f}")
    print("Market D (no predictions) correctly dropped")
    print("NaN handling works correctly")
    print("Market-wise average Brier scores:")
    for market in result.brier_scores.columns:
        market_avg = result.brier_scores[market].mean()
        print(f"  {market}: {market_avg:.4f}")


if __name__ == "__main__":
    test_calculate_brier_scores()