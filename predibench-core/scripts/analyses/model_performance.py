#!/usr/bin/env python3
"""
Comprehensive model performance analysis script.
Creates scientific graphs analyzing LLM agent performance on Polymarket prediction tasks.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import typer
from predibench.backend.data_loader import get_data_for_backend
from predibench.utils import BLUE, apply_template, get_model_color

app = typer.Typer(help="Comprehensive model performance analysis")


# LMSys Arena scores (current as of the provided data)
ARENA_SCORES = {
    "grok-4-0709": 1420,
    "gpt-5": 1440,
    "gpt-5-mini": 1389,
    "gpt-4.1": 1411,
    "o3-deep-research": None,  # N/A (not listed on leaderboard)
    "openai/gpt-oss-120b": 1350,
    "Qwen/Qwen3-Coder-480B-A35B-Instruct": 1379,
    "Qwen/Qwen3-235B-A22B-Instruct-2507": 1398,
    "deepseek-ai/DeepSeek-R1": 1394,
    "deepseek-ai/DeepSeek-V3.1": 1417,
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct": 1325,
    "meta-llama/Llama-4-Scout-17B-16E-Instruct": 1319,
    "meta-llama/Llama-3.3-70B-Instruct": 1316,  # N/A (not listed on leaderboard)
    "gemini-2.5-flash": 1406,
    "gemini-2.5-pro": 1456,
    "claude-sonnet-4-20250514": 1386,
    "claude-opus-4-1-20250805": 1438,
}

ARTIFICIAL_ANALYSIS_SCORES = {
    "grok-4-0709": 65,
    "gpt-5": 66,
    "gpt-5-mini": 61,
    "gpt-4.1": 43,
    "o3-deep-research": None,  # N/A (not listed on leaderboard)
    "openai/gpt-oss-120b": 58,
    # "Qwen/Qwen3-Coder-480B-A35B-Instruct": 1379,
    "Qwen/Qwen3-235B-A22B-Instruct-2507": 57,
    "deepseek-ai/DeepSeek-R1": 51,
    "deepseek-ai/DeepSeek-V3.1": 54,
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct": 36,
    "meta-llama/Llama-4-Scout-17B-16E-Instruct": 28,
    "meta-llama/Llama-3.3-70B-Instruct": 28,  # N/A (not listed on leaderboard)
    "gemini-2.5-flash": 51,
    "gemini-2.5-pro": 60,
    "claude-sonnet-4-20250514": 57,
    "claude-opus-4-1-20250805": 59,
}


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


def create_performance_dataframe(backend_data):
    """Create a comprehensive dataframe with all model performance metrics."""

    release_dates, inference_costs = create_model_metadata()

    performance_data = []

    for model_id, performance in backend_data.performance_per_model.items():
        release_date = release_dates.get(model_id)
        inference_cost = inference_costs.get(model_id)
        arena_score = ARENA_SCORES.get(model_id)

        performance_data.append(
            {
                "model_id": model_id,
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
                "arena_score": arena_score,
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

    colors = [
        get_model_color(model_name, i)
        for i, model_name in enumerate(df_brier["pretty_name"].unique())
    ]

    fig.add_trace(
        go.Bar(
            x=df_brier["pretty_name"],
            y=df_brier["final_brier_score"],
            name="Brier Score",
            marker=dict(color=colors),
            showlegend=False,
        )
    )

    fig.update_layout(
        xaxis_title="Model",
        yaxis_title="Brier Score",
        height=600,
        width=1000,
        xaxis_tickangle=45,
    )
    apply_template(fig)
    fig.update_layout(margin=dict(b=150, r=70))

    return fig


def create_average_return_ranking(df):
    """Create ranked bar chart for average returns."""

    # Sort by average return (descending - higher is better)
    df_return = df.sort_values("average_return_7d", ascending=False)

    fig = go.Figure()

    colors = [
        get_model_color(model_name, i)
        for i, model_name in enumerate(df_return["pretty_name"].unique())
    ]

    fig.add_trace(
        go.Bar(
            x=df_return["pretty_name"],
            y=df_return["average_return_7d"],
            name="7-day Average Return",
            marker=dict(color=colors),
            showlegend=False,
        )
    )

    fig.update_layout(
        xaxis_title="Model",
        yaxis_title="Average Return (%)",
        xaxis_tickangle=45,
        height=600,
        width=1000,
    )
    apply_template(fig)
    fig.update_layout(margin=dict(b=150, r=70))
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
        xaxis_title="Brier Score (Lower is Better)",
        yaxis_title="Average Return - 7 day (%)",
        height=600,
        width=800,
    )
    apply_template(fig)

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
        xaxis_title="Release Date",
        yaxis_title="Inference Cost per 1M tokens ($)",
        height=600,
        width=1000,
    )
    apply_template(fig)
    return fig


def create_performance_vs_arena_score_scatter(df, metric_type: str = "brier"):
    """Create scatter plot comparing model performance vs LMSys Arena score.

    Args:
        df: DataFrame with model performance data
        metric_type: Either "brier" for Brier Score or "return" for Average Return
    """

    # Filter out models without arena scores
    df_filtered = df[df["arena_score"].notna()].copy()

    if len(df_filtered) == 0:
        raise ValueError("No models found with LMSys Arena scores")

    fig = go.Figure()

    if metric_type == "brier":
        y_data = df_filtered["final_brier_score"]
        y_title = "Brier Score (Lower is Better)"
    else:
        y_data = df_filtered["average_return_7d"]
        y_title = "Average Return - 7 day (%)"

    df_filtered["pretty_name"] = df_filtered["pretty_name"].apply(
        lambda x: x
        if ("Sonnet" in x or "Gemini" in x or "GPT" in x or "Grok" in x or "R1" in x)
        else ""
    )

    fig.add_trace(
        go.Scatter(
            x=df_filtered["arena_score"],
            y=y_data,
            mode="markers+text",
            text=df_filtered["pretty_name"],
            textposition="top center",
            marker=dict(
                size=12,
                color=BLUE,
            ),
            name="Models",
            showlegend=False,
        )
    )

    fig.update_layout(
        xaxis_title="LMSys Arena Score",
        yaxis_title=y_title,
        height=600,
        width=800,
    )
    apply_template(fig)

    return fig


@app.command()
def main(
    arena_metric: str = typer.Option(
        "brier",
        help="Metric to use for arena score comparison: 'brier' for Brier Score or 'return' for Average Return",
    ),
):
    """Generate comprehensive model performance analysis including LMSys Arena comparison."""

    if arena_metric not in ["brier", "return"]:
        raise typer.BadParameter("arena_metric must be either 'brier' or 'return'")

    print("Loading backend data...")
    backend_data = get_data_for_backend()

    print("Creating performance dataframe...")
    df = create_performance_dataframe(backend_data)

    print(f"Analyzing {len(df)} models...")
    print("\nModel summary:")
    print(
        df[
            [
                "pretty_name",
                "final_brier_score",
                "average_return_7d",
                "trades_count",
                "arena_score",
            ]
        ].to_string()
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
    fig1.write_json(output_dir / "brier_score_ranking.json")

    # 2. Average return ranking
    print("Creating average return ranking...")
    fig2 = create_average_return_ranking(df)
    fig2.write_json(output_dir / "average_return_ranking.json")

    # 3. Brier vs Return scatter plot
    print("Creating Brier vs Return scatter plot...")
    fig3 = create_brier_vs_return_scatter(df)
    fig3.write_json(output_dir / "brier_vs_return_scatter.json")

    # 4. Release date and inference cost scatter plot
    print("Creating release date and inference cost analysis...")
    fig4 = create_release_date_inference_cost_scatter(df)
    fig4.write_json(output_dir / "release_date_cost_scatter.json")

    # 5. Performance vs LMSys Arena score scatter plot
    print(
        f"Creating performance vs LMSys Arena score scatter plot (using {arena_metric})..."
    )
    fig5 = create_performance_vs_arena_score_scatter(df, metric_type=arena_metric)
    fig5.write_json(output_dir / f"performance_vs_arena_score_{arena_metric}.json")

    print(f"\nAll visualizations saved to {output_dir}")


if __name__ == "__main__":
    app()
