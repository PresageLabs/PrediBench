from functools import lru_cache
from predibench.backend.data_model import LeaderboardEntry
from datetime import datetime
from predibench.backend.brier import calculate_brier_scores
from predibench.backend.data_model import DataPoint
import pandas as pd
import numpy as np
from predibench.backend.pnl import calculate_pnl
from predibench.backend.data_loader import load_agent_position, load_market_prices, load_saved_events
from predibench.backend.pnl import get_historical_returns
from predibench.backend.data_loader import load_investment_choices_from_google


def _calculate_agent_pnl_results(positions_df: pd.DataFrame, prices_df: pd.DataFrame) -> dict[str, dict]:
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

        pnl_result = calculate_pnl(positions_agent_df, prices_df)
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
            decisions_pivot_df, prices_df
        )
    
    return brier_results


def _create_pnl_history(cumulative_pnl: pd.Series) -> list[DataPoint]:
    """Convert cumulative PnL series to list of DataPoint objects for frontend."""
    pnl_history = []
    for date_idx, pnl_value in cumulative_pnl.items():
        pnl_history.append(
            DataPoint(date=date_idx.strftime("%Y-%m-%d"), value=float(pnl_value))
        )
    return pnl_history



def _aggregate_agent_performance(
    model_name: str, 
    pnl_result: dict, 
    brier_result: dict
) -> dict:
    """Aggregate all performance metrics for a single agent."""
    cumulative_pnl = pnl_result["portfolio_cumulative_pnl"]
    
    # Calculate key metrics
    final_pnl = float(cumulative_pnl.iloc[-1])
    pnl_history = _create_pnl_history(cumulative_pnl)
    
    return {
        "model_name": model_name,
        "final_cumulative_pnl": final_pnl,
        "pnl_history": pnl_history,
        "avg_brier_score": brier_result["avg_brier_score"],
    }


def _print_agent_summary(model_name: str, performance: dict):
    """Print summary metrics for an agent."""
    print(
        f"Agent {model_name}: "
        f"Profit={performance['final_cumulative_pnl']:.3f}, "
        f"Brier={performance['avg_brier_score']:.3f}"
    )


def _calculate_real_performance():
    """Calculate real performance metrics for all agents with clean separation of concerns."""
    model_results = load_investment_choices_from_google()
    saved_events = load_saved_events()
    
    positions_df =load_agent_position(model_results)
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
            brier_results[model_name]
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


def _create_leaderboard_entry(model_name: str, metrics: dict) -> LeaderboardEntry:
    """Create a LeaderboardEntry from aggregated performance metrics."""
    trend = _determine_trend(metrics["pnl_history"])
    
    return LeaderboardEntry(
        id=model_name,
        model=model_name,
        final_cumulative_pnl=metrics["final_cumulative_pnl"],
        trades=0,  # TODO: Calculate actual trades if needed
        profit=0,  # TODO: Calculate actual profit if needed  
        lastUpdated=datetime.now().strftime("%Y-%m-%d"),
        trend=trend,
        pnl_history=metrics["pnl_history"],
        avg_brier_score=metrics["avg_brier_score"],
    )


def get_leaderboard() -> list[LeaderboardEntry]:
    """Generate leaderboard from real performance data, sorted by cumulative PnL."""
    real_performance = _calculate_real_performance()

    # Sort agents by final cumulative PnL in descending order
    sorted_agents = sorted(
        real_performance.items(),
        key=lambda x: x[1]["final_cumulative_pnl"],
        reverse=True,
    )

    # Create leaderboard entries
    leaderboard = []
    for model_name, metrics in sorted_agents:
        entry = _create_leaderboard_entry(model_name, metrics)
        leaderboard.append(entry)

    return leaderboard