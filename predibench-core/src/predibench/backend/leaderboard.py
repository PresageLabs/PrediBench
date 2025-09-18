from datetime import datetime
from typing import Literal

from predibench.backend.data_model import (
    DataPoint,
    LeaderboardEntryBackend,
    ModelPerformanceBackend,
)
from predibench.utils import date_to_string


def _determine_trend(
    compound_profit_history: list[DataPoint],
) -> Literal["up", "down", "stable"]:
    """Determine the trend direction based on recent PnL changes."""
    if len(compound_profit_history) >= 2:
        recent_change = (
            compound_profit_history[-1].value - compound_profit_history[-3].value
        )
        if recent_change > 0.1:
            return "up"
        elif recent_change < -0.1:
            return "down"
        else:
            return "stable"
    return "stable"


def get_leaderboard(
    performances: list[ModelPerformanceBackend],
) -> list[LeaderboardEntryBackend]:
    """Generate leaderboard from precomputed performance data.

    Sorts by final cumulative PnL descending and builds UI-ready entries.
    """
    sorted_performances = sorted(
        performances,
        key=lambda p: p.final_profit if p.final_profit is not None else 0,
        reverse=True,
    )

    leaderboard: list[LeaderboardEntryBackend] = []
    for performance in sorted_performances:
        trend = _determine_trend(
            performance.compound_profit_history
            if performance.compound_profit_history is not None
            else []
        )

        leaderboard_entry = LeaderboardEntryBackend(
            model_id=performance.model_id,
            model_name=performance.model_name,
            trades_count=performance.trades_count,
            lastUpdated=date_to_string(datetime.now()),
            trend=trend,
            compound_profit_history=performance.compound_profit_history,
            cumulative_profit_history=performance.cumulative_profit_history,
            trades_dates=performance.trades_dates,
            average_returns=performance.average_returns,
            final_profit=performance.final_profit,
            final_brier_score=performance.final_brier_score,
            average_returns=performance.average_returns,
            sharpe=performance.sharpe,
            brier=performance.brier,
        )
        leaderboard.append(leaderboard_entry)
    return leaderboard
