from datetime import date

import pandas as pd

from predibench.logger_config import get_logger
from predibench.backend.data_model import BrierResult

logger = get_logger(__name__)


def _assert_index_is_date(df: pd.DataFrame):
    assert all(isinstance(idx, date) for idx in df.index), (
        "All index values must be date objects or timestamps without time component"
    )


def calculate_brier_scores(
    decisions_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> BrierResult:
    """
    Calculate Brier scores for model predictions.

    Args:
        decisions_df: DataFrame with model predictions/odds, with columns as markets and index as dates
        prices_df: DataFrame with market prices, with columns as markets and index as dates
        
    Returns:
        dict containing:
            - brier_scores: DataFrame with Brier scores for each market and date
            - avg_brier_score: float with average Brier score across all predictions
    """
    _assert_index_is_date(decisions_df)
    _assert_index_is_date(prices_df)

    # Get the latest price for each market as the outcome (0 or 1)
    final_prices = prices_df.iloc[-1]  # Last available price

    # Create a DataFrame to store Brier scores
    brier_scores_df = pd.DataFrame(
        index=decisions_df.index, columns=prices_df.columns
    )

    for market_id in prices_df.columns:
        # Skip markets that don't have decision data
        if market_id not in decisions_df.columns:
            continue

        # Get the outcome (final market price, should be close to 0 or 1)
        outcome = final_prices[market_id]

        # Get model predictions (odds) for this market over time
        predictions = decisions_df[market_id]

        # Calculate Brier score: (prediction - outcome)^2
        brier_scores_df[market_id] = (predictions - outcome) ** 2

    brier_scores_cleaned = brier_scores_df.dropna(how="all", axis=1)
    avg_brier_score = brier_scores_cleaned.mean().mean()
    
    return BrierResult(
        brier_scores=brier_scores_cleaned,
        avg_brier_score=float(avg_brier_score),
    )
