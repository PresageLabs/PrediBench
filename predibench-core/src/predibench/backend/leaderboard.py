from functools import lru_cache
from predibench.backend.data_model import LeaderboardEntry, AgentPerformance, PnlResult
from datetime import datetime
from predibench.backend.brier import calculate_brier_scores
from predibench.backend.data_model import DataPoint
import pandas as pd
import numpy as np
from predibench.backend.pnl import calculate_pnl
from predibench.backend.data_loader import load_agent_position, load_market_prices, load_saved_events
from predibench.backend.pnl import get_historical_returns
from predibench.backend.data_loader import load_investment_choices_from_google


def _calculate_agent_pnl_results(positions_df: pd.DataFrame, prices_df: pd.DataFrame) -> dict[str, PnlResult]:
    """Calculate PnL results for all agents using shared market data."""
    pnl_results = {}
    
    for model_name in positions_df["model_name"].unique():
        print("AGENT NAME", model_name)
        # Filter positions for this agent and convert to pivot format
        positions_agent_df = positions_df[
            positions_df["model_name"] == model_name
        ].drop(columns=["model_name"])
        
        assert len(positions_agent_df) > 0, (
            "At this stage, dataframe should not be empty!"
        )
        
        positions_agent_df = positions_agent_df.pivot(
            index="date", columns="market_id", values="choice"
        )

        pnl_result = calculate_pnl(positions_agent_df=positions_agent_df, prices_df=prices_df)
        pnl_results[model_name] = pnl_result

    return pnl_results


def _calculate_agent_brier_results(positions_df: pd.DataFrame, prices_df: pd.DataFrame) -> dict[str, dict]:
    """Calculate Brier score results for all agents using shared market data."""
    brier_results = {}
    
    for model_name in positions_df["model_name"].unique():
        # Filter decisions for this agent and convert to pivot format
        agent_decisions = positions_df[positions_df["model_name"] == model_name]
        decisions_pivot_df = agent_decisions.pivot(
            index="date", columns="market_id", values="odds"
        )
        # Align with price data
        decisions_pivot_df = decisions_pivot_df.reindex(
            prices_df.index, method="ffill"
        )
        
        brier_results[model_name] = calculate_brier_scores(
            decisions_pivot_df=decisions_pivot_df, prices_df=prices_df
        )
    
    return brier_results


# Removed _create_pnl_history - now handled directly in PnL calculation



def _aggregate_agent_performance(
    model_name: str, 
    pnl_result: PnlResult, 
    brier_result: dict,
    positions_df: pd.DataFrame
) -> AgentPerformance:
    """Aggregate all performance metrics for a single agent."""
    # Count actual trades (non-zero positions)
    model_positions = positions_df[positions_df["model_name"] == model_name]
    trades_count = len(model_positions[model_positions["choice"] != 0])
    
    return AgentPerformance(
        model_name=model_name,
        final_cumulative_pnl=pnl_result.final_pnl,
        pnl_history=pnl_result.cumulative_pnl,
        avg_brier_score=brier_result["avg_brier_score"],
        trades=trades_count,
    )


def _print_agent_summary(model_name: str, performance: AgentPerformance):
    """Print summary metrics for an agent."""
    print(
        f"Agent {model_name}: "
        f"Profit={performance.final_cumulative_pnl:.3f}, "
        f"Brier={performance.avg_brier_score:.3f}, "
        f"Trades={performance.trades}"
    )


def _calculate_real_performance() -> dict[str, AgentPerformance]:
    """Calculate real performance metrics for all agents with clean separation of concerns."""
    model_results = load_investment_choices_from_google()
    saved_events = load_saved_events()
    
    positions_df = load_agent_position(model_results)
    market_prices = load_market_prices(saved_events)
    prices_df = get_historical_returns(market_prices)

    
    # Calculate PnL and Brier results using shared data
    pnl_results = _calculate_agent_pnl_results(positions_df, prices_df)
    brier_results = _calculate_agent_brier_results(positions_df, prices_df)
    
    # Aggregate performance metrics for each agent
    agents_performance = {}
    for model_name in pnl_results.keys():
        performance = _aggregate_agent_performance(
            model_name, 
            pnl_results[model_name], 
            brier_results[model_name],
            positions_df
        )
        agents_performance[model_name] = performance
        _print_agent_summary(model_name, performance)
    
    print(f"Calculated performance for {len(agents_performance)} agents")
    return agents_performance


def _determine_trend(pnl_history: list[DataPoint]) -> str:
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


def _create_leaderboard_entry(performance: AgentPerformance) -> LeaderboardEntry:
    """Create a LeaderboardEntry from aggregated performance metrics."""
    trend = _determine_trend(performance.pnl_history)
    
    return LeaderboardEntry(
        id=performance.model_name,
        model=performance.model_name,
        final_cumulative_pnl=performance.final_cumulative_pnl,
        trades=performance.trades,
        lastUpdated=datetime.now().strftime("%Y-%m-%d"),
        trend=trend,
        pnl_history=performance.pnl_history,
        avg_brier_score=performance.avg_brier_score,
    )


def get_leaderboard() -> list[LeaderboardEntry]:
    """Generate leaderboard from real performance data, sorted by cumulative PnL."""
    real_performance = _calculate_real_performance()

    # Sort agents by final cumulative PnL in descending order
    sorted_agents = sorted(
        real_performance.items(),
        key=lambda x: x[1].final_cumulative_pnl,
        reverse=True,
    )

    # Create leaderboard entries
    leaderboard = []
    for _, performance in sorted_agents:
        entry = _create_leaderboard_entry(performance)
        leaderboard.append(entry)

    return leaderboard