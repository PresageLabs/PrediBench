from datetime import datetime
from typing import Literal

from predibench.backend.data_model import (
    DataPoint,
    LeaderboardEntryBackend,
    ModelPerformanceBackend,
)
from predibench.utils import date_to_string


def _determine_trend(
    position_values_history: list[DataPoint],
) -> Literal["up", "down", "stable"]:
    """Determine the trend direction based on recent PnL changes."""
    if len(position_values_history) >= 2:
        recent_change = (
            position_values_history[-1].value - position_values_history[-3].value
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
        key=lambda p: p.final_positions_value
        if p.final_positions_value is not None
        else 0,
        reverse=True,
    )

    leaderboard: list[LeaderboardEntryBackend] = []
    for performance in sorted_performances:
        trend = _determine_trend(
            performance.position_values_history
            if performance.position_values_history is not None
            else []
        )

        leaderboard_entry = LeaderboardEntryBackend(
            model_id=performance.model_id,
            model_name=performance.model_name,
            trades_count=performance.trades_count,
            lastUpdated=date_to_string(datetime.now()),
            trend=trend,
            position_values_history=performance.position_values_history,
            final_positions_value=performance.final_positions_value,
            final_brier_score=performance.final_brier_score,
        )
        leaderboard.append(leaderboard_entry)
    return leaderboard
