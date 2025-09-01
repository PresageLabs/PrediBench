from datetime import date

import numpy as np
import pandas as pd

from predibench.backend.leaderboard import _calculate_agent_brier_results


def test_calculate_agent_brier_results_two_models_with_nones():
    """
    Validate Brier scores per model with mixed None values and alignment to prices index.

    - Two models (ModelA, ModelB)
    - Two markets (market_A, market_B)
    - Decisions contain None (missing predictions on some days)
    - Prices contain None (market inactivity on some days)

    Expectation:
    - Reindexing to prices_df.index with ffill fills forward decisions
    - Only markets present in decisions are scored per model
    - Average Brier score equals the mean of all scored entries per model
    """
    # Dates
    dates = [date(2024, 1, i) for i in range(1, 7)]  # 6 days

    # Build positions_df-like structure with required columns for two models
    # We'll supply only 'date', 'market_id', 'odds', 'model_name'
    records = []

    # ModelA decisions
    # market_A predictions with None gaps
    model_a_market_a = [None, 0.6, None, 0.8, None, 0.9]
    # market_B fewer predictions
    model_a_market_b = [0.3, None, None, 0.4, 0.5, None]

    for d, pa, pb in zip(dates, model_a_market_a, model_a_market_b):
        if pa is not None:
            records.append({
                "date": d,
                "market_id": "market_A",
                "odds": pa,
                "model_name": "ModelA",
                "choice": 0.0,
            })
        if pb is not None:
            records.append({
                "date": d,
                "market_id": "market_B",
                "odds": pb,
                "model_name": "ModelA",
                "choice": 0.0,
            })

    # ModelB decisions - different pattern
    model_b_market_a = [0.2, None, 0.5, None, 0.7, None]
    model_b_market_b = [None, 0.9, None, 0.6, None, 0.4]

    for d, pa, pb in zip(dates, model_b_market_a, model_b_market_b):
        if pa is not None:
            records.append({
                "date": d,
                "market_id": "market_A",
                "odds": pa,
                "model_name": "ModelB",
                "choice": 0.0,
            })
        if pb is not None:
            records.append({
                "date": d,
                "market_id": "market_B",
                "odds": pb,
                "model_name": "ModelB",
                "choice": 0.0,
            })

    positions_df = pd.DataFrame.from_records(records)

    # Prices with None that will be carried forward in brier routine via final row only
    prices_df = pd.DataFrame({
        "market_A": [None, 0.4, 0.6, None, 1.0, 1.0],
        "market_B": [0.2, None, 0.3, 0.3, None, 0.0],
    }, index=dates)

    # To mimic leaderboard code, we pass positions_df and prices_df
    brier_results = _calculate_agent_brier_results(positions_df, prices_df)

    # Validate both models present
    assert set(brier_results.keys()) == {"ModelA", "ModelB"}

    # Extract outcomes (final prices)
    outcome_A = prices_df.iloc[-1]["market_A"]  # 1.0
    outcome_B = prices_df.iloc[-1]["market_B"]  # 0.0

    # Helper to compute expected brier series given raw decisions (with ffill after reindex)
    def expected_series(decisions_list, outcome):
        # Build a series on dates, then ffill to align to prices index length
        s = pd.Series(decisions_list, index=dates)
        s_ffill = s.reindex(dates).ffill()
        return (s_ffill - outcome) ** 2

    # ModelA expectations: use only days where decisions exist, but after reindex+ffill they extend
    model_a_market_a_series = pd.Series(model_a_market_a, index=dates).reindex(dates).ffill()
    model_a_market_b_series = pd.Series(model_a_market_b, index=dates).reindex(dates).ffill()

    expected_a_market_a = (model_a_market_a_series - outcome_A) ** 2
    expected_a_market_b = (model_a_market_b_series - outcome_B) ** 2

    # ModelB expectations
    model_b_market_a_series = pd.Series(model_b_market_a, index=dates).reindex(dates).ffill()
    model_b_market_b_series = pd.Series(model_b_market_b, index=dates).reindex(dates).ffill()

    expected_b_market_a = (model_b_market_a_series - outcome_A) ** 2
    expected_b_market_b = (model_b_market_b_series - outcome_B) ** 2

    # Assert brier scores columns present per model according to decisions
    # ModelA decided on both markets at least once -> both columns expected
    assert set(brier_results["ModelA"].brier_scores.columns) == {"market_A", "market_B"}
    # ModelB also decided on both
    assert set(brier_results["ModelB"].brier_scores.columns) == {"market_A", "market_B"}

    # Compare arrays
    np.testing.assert_array_almost_equal(
        brier_results["ModelA"].brier_scores["market_A"].values,
        expected_a_market_a.values,
        decimal=6,
    )
    np.testing.assert_array_almost_equal(
        brier_results["ModelA"].brier_scores["market_B"].values,
        expected_a_market_b.values,
        decimal=6,
    )
    np.testing.assert_array_almost_equal(
        brier_results["ModelB"].brier_scores["market_A"].values,
        expected_b_market_a.values,
        decimal=6,
    )
    np.testing.assert_array_almost_equal(
        brier_results["ModelB"].brier_scores["market_B"].values,
        expected_b_market_b.values,
        decimal=6,
    )

    # Validate averages
    expected_avg_a = float(pd.concat([expected_a_market_a, expected_a_market_b], axis=1).mean().mean())
    expected_avg_b = float(pd.concat([expected_b_market_a, expected_b_market_b], axis=1).mean().mean())

    assert abs(brier_results["ModelA"].avg_brier_score - expected_avg_a) < 1e-8
    assert abs(brier_results["ModelB"].avg_brier_score - expected_avg_b) < 1e-8

if __name__ == "__main__":
    test_calculate_agent_brier_results_two_models_with_nones()