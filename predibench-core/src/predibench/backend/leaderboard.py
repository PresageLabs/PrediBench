from functools import lru_cache
from predibench.backend.data_model import LeaderboardEntry
from datetime import datetime
from predibench.backend.brier import BrierScoreCalculator
from predibench.backend.data_model import DataPoint
import pandas as pd
import numpy as np
from predibench.backend.pnl import get_pnls
from predibench.backend.data_loader import load_agent_position




@lru_cache(maxsize=1)
def _calculate_real_performance():
    """Calculate real Profit and performance metrics exactly like gradio app"""
    positions_df = load_agent_position()
    
    pnl_calculators = get_pnls(
        positions_df
    )

    brier_calculators = {}
    for model_name, pnl_calculator in pnl_calculators.items():
        # Filter decisions for this agent
        agent_decisions = positions_df[positions_df["model_name"] == model_name]
        # Convert to pivot format
        decisions_pivot_df = agent_decisions.pivot(
            index="date", columns="market_id", values="odds"
        )
        # Align with PnL calculator's price data
        decisions_pivot_df = decisions_pivot_df.reindex(
            pnl_calculator.prices.index, method="ffill"
        )
        brier_calculators[model_name] = BrierScoreCalculator(
            decisions_pivot_df, pnl_calculator.prices
        )

    agents_performance = {}
    for model_name, pnl_calculator in pnl_calculators.items():
        brier_calculator = brier_calculators[model_name]
        daily_pnl = pnl_calculator.portfolio_daily_pnl

        # Generate performance history from cumulative Profit
        cumulative_pnl = pnl_calculator.portfolio_cumulative_pnl
        pnl_history = []
        for date_idx, pnl_value in cumulative_pnl.items():
            pnl_history.append(
                DataPoint(date=date_idx.strftime("%Y-%m-%d"), value=float(pnl_value))
            )

        # Calculate metrics exactly like gradio
        final_pnl = float(pnl_calculator.portfolio_cumulative_pnl.iloc[-1])
        sharpe_ratio = (
            float((daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252))
            if daily_pnl.std() > 0
            else 0
        )

        agents_performance[model_name] = {
            "model_name": model_name,
            "final_cumulative_pnl": final_pnl,
            "annualized_sharpe_ratio": sharpe_ratio,
            "pnl_history": pnl_history,
            "daily_cumulative_pnl": pnl_calculator.portfolio_cumulative_pnl.tolist(),
            "dates": [
                d.strftime("%Y-%m-%d")
                for d in pnl_calculator.portfolio_cumulative_pnl.index.tolist()
            ],
            "avg_brier_score": brier_calculator.avg_brier_score,
        }

        print(
            f"Agent {model_name}: Profit={final_pnl:.3f}, Sharpe={sharpe_ratio:.3f}, Brier={brier_calculator.avg_brier_score:.3f}"
        )

    print(f"Calculated performance for {len(agents_performance)} agents")
    return agents_performance


# Generate leaderboard from real data only
@lru_cache(maxsize=1)
def get_leaderboard() -> list[LeaderboardEntry]:
    real_performance = _calculate_real_performance()

    leaderboard = []
    for _, (model_name, metrics) in enumerate(
        sorted(
            real_performance.items(),
            key=lambda x: x[1]["final_cumulative_pnl"],
            reverse=True,
        )
    ):
        # Determine trend
        history = metrics["pnl_history"]
        if len(history) >= 2:
            recent_change = history[-1].value - history[-2].value
            trend = (
                "up"
                if recent_change > 0.1
                else "down"
                if recent_change < -0.1
                else "stable"
            )
        else:
            trend = "stable"

        entry = LeaderboardEntry(
            id=model_name,
            model=model_name,
            final_cumulative_pnl=metrics["final_cumulative_pnl"],
            trades=0,
            profit=0,
            lastUpdated=datetime.now().strftime("%Y-%m-%d"),
            trend=trend,
            pnl_history=metrics["pnl_history"],
            avg_brier_score=metrics["avg_brier_score"],
        )
        leaderboard.append(entry)

    return leaderboard
