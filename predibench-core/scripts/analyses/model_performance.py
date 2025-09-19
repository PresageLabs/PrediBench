#!/usr/bin/env python3
"""
Comprehensive model performance analysis script.
Creates scientific graphs analyzing LLM agent performance on Polymarket prediction tasks.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from predibench.backend.data_loader import get_data_for_backend
from predibench.utils import apply_template


def create_model_metadata():
    """Create notional tables for model release dates and inference prices."""

    # Model release dates (ISO format YYYY-MM-DD)
    release_dates = {
        "grok-4-0709": "2025-07-09",
        "gpt-5": "2025-08-07",
        "gpt-5-mini": "2025-08-07",
        "gpt-4.1": "2025-04-14",
        "o3-deep-research": "2025-04-16",
        "openai/gpt-oss-120b": "2025-08-05",
        "Qwen/Qwen3-Coder-480B-A35B-Instruct": "2025-08-13",
        "Qwen/Qwen3-235B-A22B-Instruct-2507": "2025-04-29",
        "deepseek-ai/DeepSeek-R1": "2025-01-10",
        "deepseek-ai/DeepSeek-V3.1": "2025-08-21",
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct": "2025-04-05",
        "meta-llama/Llama-4-Scout-17B-16E-Instruct": "2025-04-05",
        "meta-llama/Llama-3.3-70B-Instruct": "2024-12-03",
        "gemini-2.5-flash": "2025-04-04",
        "gemini-2.5-pro": "2025-04-04",
        "sonar-deep-research": "2025-03-07",
        "claude-sonnet-4-20250514": "2025-05-14",
        "claude-opus-4.1-20250805": "2025-08-05",
        "test_random": None,  # baseline
        "most_likely_volume_proportional": None,  # baseline
    }

    # Output cost per 1M tokens (USD)
    inference_costs = {
        "grok-4-0709": 15.0,
        "gpt-5": 10.0,
        "gpt-5-mini": 2.0,
        "gpt-4.1": 8.0,
        "o3-deep-research": 8.0,
        "openai/gpt-oss-120b": 0.25,
        "Qwen/Qwen3-Coder-480B-A35B-Instruct": 1.80,
        "Qwen/Qwen3-235B-A22B-Instruct-2507": 0.88,
        "deepseek-ai/DeepSeek-R1": 2.19,
        "deepseek-ai/DeepSeek-V3.1": 1.68,
        "meta-llama/Llama-4-Maverick-17B-128E-Instruct": 0.60,
        "meta-llama/Llama-4-Scout-17B-16E-Instruct": 0.30,
        "meta-llama/Llama-3.3-70B-Instruct": 0.40,
        "gemini-2.5-flash": 0.30,
        "gemini-2.5-pro": 10.0,
        "sonar-deep-research": 8.0,
        "claude-sonnet-4-20250514": 15.0,
        "claude-opus-4.1-20250805": 75.0,
        "test_random": None,  # baseline
        "most_likely_volume_proportional": None,  # baseline
    }

    return release_dates, inference_costs


def extract_model_name(model_id: str) -> str:
    """Canonical model key used in metadata lookups.

    For this analysis, we treat the raw model_id as the canonical key.
    """
    return model_id


def create_performance_dataframe(backend_data):
    """Create a comprehensive dataframe with all model performance metrics."""

    release_dates, inference_costs = create_model_metadata()

    performance_data = []

    for model_id, performance in backend_data.performance_per_model.items():
        model_key = extract_model_name(model_id)
        release_date = release_dates.get(model_key)
        inference_cost = inference_costs.get(model_key)

        performance_data.append(
            {
                "model_id": model_id,
                "model_key": model_key,
                "pretty_name": performance.model_name,  # from BackendData
                "final_brier_score": performance.final_brier_score,
                "final_profit": performance.final_profit,
                "average_return_1d": performance.average_returns.one_day_return,
                "average_return_2d": performance.average_returns.two_day_return,
                "average_return_7d": performance.average_returns.seven_day_return,
                "average_return_all": performance.average_returns.all_time_return,
                "sharpe_1d": performance.sharpe.one_day_annualized_sharpe,
                "sharpe_2d": performance.sharpe.two_day_annualized_sharpe,
                "sharpe_7d": performance.sharpe.seven_day_annualized_sharpe,
                "trades_count": performance.trades_count,
                "release_date": release_date,
                "inference_cost": inference_cost,
            }
        )

    df = pd.DataFrame(performance_data)
    df["release_date"] = pd.to_datetime(df["release_date"])

    return df


def create_brier_score_ranking(df):
    """Create ranked bar chart for Brier scores."""

    # Sort by Brier score (ascending - lower is better)
    df_brier = df.sort_values("final_brier_score")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_brier["pretty_name"],
            y=df_brier["final_brier_score"],
            name="Brier Score",
            marker_color="lightcoral",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Ranked Brier Scores (Lower is Better)",
        xaxis_title="Model",
        yaxis_title="Brier Score",
        xaxis_tickangle=45,
        height=600,
        width=1000,
    )

    return fig


def create_average_return_ranking(df):
    """Create ranked bar chart for average returns."""

    # Sort by average return (descending - higher is better)
    df_return = df.sort_values("average_return_7d", ascending=False)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_return["pretty_name"],
            y=df_return["average_return_7d"],
            name="7-day Average Return",
            marker_color="lightblue",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Ranked Average Returns (7-day)",
        xaxis_title="Model",
        yaxis_title="Average Return (%)",
        xaxis_tickangle=45,
        height=600,
        width=1000,
    )

    return fig


def create_brier_vs_return_scatter(df):
    """Create scatter plot comparing Brier scores vs Average Returns."""

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["final_brier_score"],
            y=df["average_return_7d"],
            mode="markers+text",
            text=df["pretty_name"],
            textposition="top center",
            marker=dict(
                size=10,
                color=df["trades_count"],
                colorscale="Viridis",
                colorbar=dict(title="Number of Trades"),
                line=dict(width=1, color="black"),
            ),
            name="Models",
        )
    )

    fig.update_layout(
        title="Brier Score vs Average Return (7-day)",
        xaxis_title="Brier Score (Lower is Better)",
        yaxis_title="Average Return - 7 day (%)",
        height=600,
        width=800,
    )

    return fig


def create_release_date_inference_cost_scatter(df):
    """Create scatter plot showing average return vs release date and inference cost."""

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["release_date"],
            y=df["inference_cost"],
            mode="markers+text",
            text=df["pretty_name"],
            textposition="middle center",
            marker=dict(
                size=40,
                color=df["average_return_7d"],
                colorscale="RdYlGn",
                cmid=0,
                symbol="square",
                colorbar=dict(title="Average Return 7d (%)"),
                line=dict(width=2, color="black"),
            ),
            name="Models",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Average Return by Release Date and Inference Cost",
        xaxis_title="Release Date",
        yaxis_title="Inference Cost per 1M tokens ($)",
        height=600,
        width=1000,
    )

    return fig


def main():
    print("Loading backend data...")
    backend_data = get_data_for_backend()

    print("Creating performance dataframe...")
    df = create_performance_dataframe(backend_data)

    print(f"Analyzing {len(df)} models...")
    print("\nModel summary:")
    print(
        df[["pretty_name", "final_brier_score", "average_return_7d", "trades_count"]]
        .to_string()
    )

    # Create output directory under frontend public at the repo root
    repo_root = Path(__file__).resolve().parents[3]
    study_name = "model_performance_comprehensive_analysis"
    output_dir = repo_root / "predibench-frontend-react/public" / study_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nCreating visualizations in {output_dir}...")

    # 1. Brier score ranking
    print("Creating Brier score ranking...")
    fig1 = create_brier_score_ranking(df)
    apply_template(fig1)
    fig1.write_json(output_dir / "brier_score_ranking.json")

    # 2. Average return ranking
    print("Creating average return ranking...")
    fig2 = create_average_return_ranking(df)
    apply_template(fig2)
    fig2.write_json(output_dir / "average_return_ranking.json")

    # 3. Brier vs Return scatter plot
    print("Creating Brier vs Return scatter plot...")
    fig3 = create_brier_vs_return_scatter(df)
    apply_template(fig3)
    fig3.write_json(output_dir / "brier_vs_return_scatter.json")

    # 4. Release date and inference cost scatter plot
    print("Creating release date and inference cost analysis...")
    fig4 = create_release_date_inference_cost_scatter(df)
    apply_template(fig4)
    fig4.write_json(output_dir / "release_date_cost_scatter.json")

    print(f"\nAnalysis complete! Files saved to {output_dir}")
    print("Generated files:")
    print("- brier_score_ranking.json")
    print("- average_return_ranking.json")
    print("- brier_vs_return_scatter.json")
    print("- release_date_cost_scatter.json")


if __name__ == "__main__":
    main()
