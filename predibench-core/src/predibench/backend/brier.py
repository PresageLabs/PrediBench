from datetime import date

import pandas as pd

from predibench.logger_config import get_logger

logger = get_logger(__name__)


class BrierScoreCalculator:
    def __init__(
        self,
        decisions_df: pd.DataFrame,
        prices_df: pd.DataFrame,
    ):
        """
        Calculate Brier scores for model predictions.

        Args:
            decisions_df: DataFrame with model predictions/odds, with columns as markets and index as dates
            prices_df: DataFrame with market prices, with columns as markets and index as dates
        """
        self.decisions_df = decisions_df
        self.prices_df = prices_df
        self._assert_index_is_date(self.decisions_df)
        self._assert_index_is_date(self.prices_df)

        # Calculate Brier scores
        self.brier_scores = self.calculate_brier_scores()
        self.avg_brier_score = self.brier_scores.mean().mean()

    def _assert_index_is_date(self, df: pd.DataFrame):
        assert all(isinstance(idx, date) for idx in df.index), (
            "All index values must be date objects or timestamps without time component"
        )

    def calculate_brier_scores(self):
        """
        Calculate Brier scores for each market based on model predictions (odds) vs actual outcomes (final prices).
        Brier Score = (prediction - outcome)^2
        Lower scores are better (0 is perfect, 1 is worst possible).
        """
        # Get the latest price for each market as the outcome (0 or 1)
        final_prices = self.prices_df.iloc[-1]  # Last available price

        # Create a DataFrame to store Brier scores
        brier_scores_df = pd.DataFrame(
            index=self.decisions_df.index, columns=self.prices_df.columns
        )

        for market_id in self.prices_df.columns:
            # Skip markets that don't have decision data
            if market_id not in self.decisions_df.columns:
                continue

            # Get the outcome (final market price, should be close to 0 or 1)
            outcome = final_prices[market_id]

            # Get model predictions (odds) for this market over time
            predictions = self.decisions_df[market_id]

            # Calculate Brier score: (prediction - outcome)^2
            brier_scores_df[market_id] = (predictions - outcome) ** 2

        return brier_scores_df.dropna(how="all", axis=1)
