from datetime import datetime
from predibench.backend.data_model import (
    LeaderboardEntryBackend,
    ModelPerformanceBackend,
    TimeseriesPointBackend,
)


def _determine_trend(pnl_history: list[TimeseriesPointBackend]) -> str:
    """Determine the trend direction based on recent PnL changes."""
    if len(pnl_history) >= 2:
        recent_change = pnl_history[-1].value - pnl_history[-2].value
        if recent_change > 0.1:
            return "up"
        elif recent_change < -0.1:
            return "down"
        else:
            return "stable"
    return "stable"


def _create_leaderboard_entry(performance: ModelPerformanceBackend) -> LeaderboardEntryBackend:
    """Create a LeaderboardEntry from aggregated performance metrics."""
    trend = _determine_trend(performance.cummulative_pnl)
    
    return LeaderboardEntryBackend(
        id=performance.model_name,
        model=performance.model_name,
        final_cumulative_pnl=performance.final_pnl,
        trades=getattr(performance, "trades", len(performance.trades_dates)),
        lastUpdated=datetime.now().strftime("%Y-%m-%d"),
        trend=trend,
        pnl_history=performance.cummulative_pnl,
        avg_brier_score=performance.final_brier_score,
    )

def get_leaderboard(performance: list[ModelPerformanceBackend]) -> list[LeaderboardEntryBackend]:
    """Generate leaderboard from precomputed performance data.

    Sorts by final cumulative PnL descending and builds UI-ready entries.
    """
    sorted_performance = sorted(
        performance,
        key=lambda p: p.final_pnl,
        reverse=True,
    )

    leaderboard: list[LeaderboardEntryBackend] = []
    for perf in sorted_performance:
        leaderboard.append(_create_leaderboard_entry(perf))
    return leaderboard
