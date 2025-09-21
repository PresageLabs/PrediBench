#!/usr/bin/env python3
"""
Bet Amount vs Kelly Criterion Analysis

This script analyzes whether models perform better using their own bet amounts
versus bet amounts computed from their probability estimates using Kelly criterion.

The analysis compares 7-day average returns using original bet amounts vs Kelly-derived bet amounts.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from predibench.backend.data_loader import get_data_for_backend
from predibench.utils import apply_template, get_model_color
from predibench.common import FRONTEND_PUBLIC_PATH

def kelly_bet_amount(estimated_prob: float, market_price: float) -> float:
    """
    Calculate optimal Kelly bet amount given estimated probability and market price.

    Args:
        estimated_prob: Model's estimated probability of the event
        market_price: Market price (implied probability)

    Returns:
        Kelly optimal bet amount (positive for YES bets, negative for NO bets)
    """
    if market_price <= 0 or market_price >= 1:
        return 0

    # Kelly formula for binary outcomes
    if estimated_prob > market_price:
        # Betting YES: Kelly = (bp - q) / b where b=odds-1, p=prob, q=1-p
        odds_for_yes = (1 - market_price) / market_price
        kelly_bet = (estimated_prob * odds_for_yes - (1 - estimated_prob)) / odds_for_yes
        return max(0, min(1, kelly_bet))  # Clamp to [0, 1]
    elif estimated_prob < market_price:
        # Betting NO: Similar formula but for the opposite outcome
        odds_for_no = market_price / (1 - market_price)
        kelly_bet = ((1 - estimated_prob) * odds_for_no - estimated_prob) / odds_for_no
        return -max(0, min(1, kelly_bet))  # Negative for NO bets
    else:
        return 0

def calculate_model_average_returns_from_decisions(backend_data, use_kelly: bool = False) -> dict:
    """
    Calculate average returns across all event decisions for each model,
    matching the leaderboard calculation exactly.

    Returns:
        Dict mapping model_id to {seven_day_return, sharpe_ratio, total_return}
    """
    model_results = {}

    # Get the data with or without Kelly recomputation
    if use_kelly:
        data = get_data_for_backend(recompute_bets_with_kelly_criterion=True)
    else:
        data = backend_data

    # Group model decisions by model_id
    decisions_by_model = {}
    for decision in data.model_decisions:
        if "baseline" in decision.model_info.inference_provider.lower():
            continue
        if decision.model_id not in decisions_by_model:
            decisions_by_model[decision.model_id] = []
        decisions_by_model[decision.model_id].append(decision)

    for model_id, decisions in decisions_by_model.items():
        # Collect all event decision returns (exactly like in compute_profits.py)
        all_seven_day_returns = []

        model_name = decisions[0].model_info.model_pretty_name

        for decision in decisions:
            for event_decision in decision.event_investment_decisions:
                if event_decision.returns is not None:
                    all_seven_day_returns.append(event_decision.returns.seven_day_return)

        if all_seven_day_returns:
            # Calculate average return (matching the leaderboard exactly)
            avg_seven_day_return = float(np.mean(all_seven_day_returns))

            # Calculate Sharpe ratio from the returns variance
            if len(all_seven_day_returns) >= 2:
                returns_array = np.array(all_seven_day_returns)
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array, ddof=1)

                if std_return > 0 and not np.isnan(std_return):
                    sharpe_ratio = mean_return / std_return
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0

            # Get compound portfolio return from the performance data
            if model_id in data.performance_per_model:
                total_return = data.performance_per_model[model_id].final_profit
            else:
                total_return = 0.0

            model_results[model_id] = {
                "model_name": model_name,
                "seven_day_return": avg_seven_day_return,
                "sharpe_ratio": sharpe_ratio,
                "total_return": total_return
            }

    return model_results

def analyze_bet_strategies(backend_data) -> pd.DataFrame:
    """
    Analyze performance of original bet amounts vs Kelly-derived bet amounts.

    Returns:
        DataFrame with columns: model_name, strategy_type, seven_day_return, sharpe_ratio, total_return
    """
    strategy_results = []

    # Calculate original strategy results
    print("Calculating original strategy results...")
    original_results = calculate_model_average_returns_from_decisions(backend_data, use_kelly=False)

    for model_id, metrics in original_results.items():
        strategy_results.append({
            "model_id": model_id,
            "model_name": metrics["model_name"],
            "strategy_type": "Original",
            "seven_day_return": metrics["seven_day_return"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "total_return": metrics["total_return"]
        })

    # Calculate Kelly strategy results
    print("Calculating Kelly strategy results...")
    kelly_results = calculate_model_average_returns_from_decisions(backend_data, use_kelly=True)

    for model_id, metrics in kelly_results.items():
        strategy_results.append({
            "model_id": model_id,
            "model_name": metrics["model_name"],
            "strategy_type": "Kelly",
            "seven_day_return": metrics["seven_day_return"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "total_return": metrics["total_return"]
        })

    return pd.DataFrame(strategy_results)

def create_seven_day_return_comparison_chart(strategy_df: pd.DataFrame) -> go.Figure:
    """Create enhanced comparison chart for 7-day return performance."""

    fig = go.Figure()

    if strategy_df.empty:
        fig.add_annotation(text="No performance data found",
                          xref="paper", yref="paper", x=0.5, y=0.5)
        apply_template(fig, width=1400, height=800)
        return fig

    # Pivot data for easier plotting
    pivot_df = strategy_df.pivot(index="model_name", columns="strategy_type", values="seven_day_return").reset_index()

    # Calculate difference (Kelly - Original)
    pivot_df["difference"] = pivot_df["Kelly"] - pivot_df["Original"]
    pivot_df["improvement"] = pivot_df["difference"] > 0

    # Sort by original bet amount performance (7-day returns), best to worst
    pivot_df = pivot_df.sort_values("Original", ascending=False)

    # Create grouped bar chart
    models = pivot_df["model_name"]
    original_values = pivot_df["Original"]
    kelly_values = pivot_df["Kelly"]

    fig.add_trace(
        go.Bar(
            name="Original Bet Amounts",
            x=models,
            y=original_values,
            marker_color="#FF6B6B",
            opacity=0.8,
            text=[f"{val:.2%}" for val in original_values],
            textposition="outside",
            textfont=dict(size=10)
        )
    )

    fig.add_trace(
        go.Bar(
            name="Kelly-Derived Bet Amounts",
            x=models,
            y=kelly_values,
            marker_color="#4ECDC4",
            opacity=0.8,
            text=[f"{val:.2%}" for val in kelly_values],
            textposition="outside",
            textfont=dict(size=10)
        )
    )

    # Update layout with improved spacing and margins
    fig.update_layout(
        xaxis_title="Model",
        yaxis_title="7-Day Average Return",
        barmode="group",
        xaxis_tickangle=-45,
        height=800,
        width=1400,
        showlegend=True,
        margin=dict(l=100, r=100, t=100, b=200),  # Increased bottom margin for model names
        xaxis=dict(
            tickfont=dict(size=12),
            tickmode='array',
            tickvals=list(range(len(models))),
            ticktext=models,
            side='bottom'
        ),
        yaxis=dict(
            tickformat=".1%",
            tickfont=dict(size=12)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12)
        )
    )

    # Add horizontal line at y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    apply_template(fig, width=1400, height=800)
    return fig

def save_plotly_figure_as_json(strategy_df: pd.DataFrame) -> None:
    """Save the Plotly figure as JSON for the frontend."""

    # Create the Plotly figure
    fig = create_seven_day_return_comparison_chart(strategy_df)

    # Save to frontend public directory in market_dynamics folder
    output_dir = FRONTEND_PUBLIC_PATH / "market_dynamics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "bet_strategy_comparison.json"

    # Save as Plotly figure JSON
    fig.write_json(output_path)

    print(f"Plotly figure saved as JSON: {output_path}")

def main():
    """Main analysis function."""
    print("Loading backend data with original bet amounts...")

    # Analyze bet strategies
    print("Analyzing performance differences between original and Kelly-derived bet amounts...")
    strategy_df = analyze_bet_strategies(get_data_for_backend())

    if strategy_df.empty:
        print("No strategy data found!")
        return

    print(f"Analyzed {len(strategy_df['model_name'].unique())} models")

    # Create output directory
    output_dir = Path("/Users/charlesazam/charloupioupiou/market-bench/analyses/bet_strategy_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create 7-day return comparison visualization
    print("Creating 7-day return comparison chart...")
    fig_7day = create_seven_day_return_comparison_chart(strategy_df)
    fig_7day.write_html(output_dir / "seven_day_return_comparison.html")

    # Save Plotly figure as JSON for frontend
    print("Saving Plotly figure as JSON for frontend...")
    save_plotly_figure_as_json(strategy_df)

    # Print summary statistics for 7-day return only
    print("\n=== ANALYSIS SUMMARY ===")

    pivot_df = strategy_df.pivot(index="model_name", columns="strategy_type", values="seven_day_return").reset_index()
    pivot_df = pivot_df.dropna()

    if not pivot_df.empty:
        pivot_df["improvement"] = pivot_df["Kelly"] - pivot_df["Original"]
        improved_count = (pivot_df["improvement"] > 0).sum()
        total_count = len(pivot_df)
        avg_improvement = pivot_df["improvement"].mean()

        print(f"\n7-Day Return:")
        print(f"  Models improved with Kelly: {improved_count}/{total_count} ({improved_count/total_count*100:.1f}%)")
        print(f"  Average improvement: {avg_improvement:.3f} ({avg_improvement*100:.2f}%)")

        # Top improvers
        top_improvers = pivot_df.nlargest(3, "improvement")
        print(f"  Top improvers:")
        for _, row in top_improvers.iterrows():
            print(f"    {row['model_name']}: {row['improvement']:.3f} ({row['improvement']*100:.2f}%)")

    print(f"\nAnalysis complete! Results saved to: {output_dir}")

if __name__ == "__main__":
    main()