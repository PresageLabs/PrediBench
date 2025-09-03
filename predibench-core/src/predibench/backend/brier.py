from datetime import date

import pandas as pd
from pydantic import BaseModel

from predibench.logger_config import get_logger
import numpy as np

logger = get_logger(__name__)


class BrierResult(BaseModel):
    """Clean, typed result from Brier score calculation"""
    # DataFrame of per-date Brier scores per market (nullable when no decisions)
    brier_scores: pd.DataFrame
    # Average Brier score across all available predictions
    avg_brier_score: float
    
    class Config:
        arbitrary_types_allowed = True


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


def compute_brier_scores_df(
    decisions_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the per-date, per-market Brier scores DataFrame for a model.

    Returns a DataFrame with index as dates and columns as market_ids. Values are
    (prediction - final_outcome)^2. Missing predictions remain NaN.
    """
    _assert_index_is_date(decisions_df)
    _assert_index_is_date(prices_df)

    # Align decisions to full price index and forward-fill predictions
    decisions_aligned = decisions_df.reindex(prices_df.index).ffill()

    # Use last available price as proxy for outcome (close to 0 or 1)
    final_prices = prices_df.iloc[-1]

    # Compute Brier per market where we have predictions
    common_markets = [c for c in decisions_aligned.columns if c in prices_df.columns]
    if not common_markets:
        # Return empty frame with aligned index
        return pd.DataFrame(index=prices_df.index)

    # Broadcast final prices across index and compute squared error
    final_prices_broadcast = pd.DataFrame(
        np.tile(final_prices[common_markets].to_numpy(), (len(decisions_aligned.index), 1)),
        index=decisions_aligned.index,
        columns=common_markets,
    )
    brier_df = (decisions_aligned[common_markets] - final_prices_broadcast) ** 2
    return brier_df
