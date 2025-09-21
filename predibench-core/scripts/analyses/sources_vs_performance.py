#!/usr/bin/env python3
"""
Sources vs Performance Analysis Script.
Investigates the correlation between number of sources used and model performance.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from predibench.backend.data_loader import get_data_for_backend
from predibench.utils import apply_template
from scipy import stats


def extract_model_level_data(backend_data):
    """Extract model-level performance metrics and aggregate sources usage."""

    model_data = []

    for model_id, performance in backend_data.performance_per_model.items():
        # Find all decisions for this model to calculate source statistics
        model_decisions = []
        model_name = None

        for model_decision in backend_data.model_decisions:
            if model_decision.model_id == model_id:
                if model_name is None:
                    model_name = model_decision.model_info.model_pretty_name

                # Extract sources for each event decision
                for event_decision in model_decision.event_investment_decisions:
                    google_sources = event_decision.sources_google or []
                    webpage_sources = event_decision.sources_visit_webpage or []

                    model_decisions.append(
                        {
                            "google_sources_count": len(google_sources),
                            "webpage_sources_count": len(webpage_sources),
                            "total_sources_count": len(google_sources)
                            + len(webpage_sources),
                        }
                    )

        if not model_decisions:
            continue

        # Calculate source usage statistics for this model
        sources_df = pd.DataFrame(model_decisions)

        # Special handling for Sonar Deep Research - assign 20 Google + 16.5 webpage sources
        if model_name and "Sonar Deep Research" in model_name:
            mean_total_sources = 36.5
            median_total_sources = 36.5
            mean_google_sources = 20.0
            median_google_sources = 20.0
            mean_webpage_sources = 16.5
            median_webpage_sources = 16
        else:
            mean_total_sources = sources_df["total_sources_count"].mean()
            median_total_sources = sources_df["total_sources_count"].median()
            mean_google_sources = sources_df["google_sources_count"].mean()
            median_google_sources = sources_df["google_sources_count"].median()
            mean_webpage_sources = sources_df["webpage_sources_count"].mean()
            median_webpage_sources = sources_df["webpage_sources_count"].median()

        model_data.append(
            {
                "model_id": model_id,
                "model_name": model_name,
                "final_brier_score": performance.final_brier_score,
                "average_return_1d": performance.average_returns.one_day_return,
                "average_return_7d": performance.average_returns.seven_day_return,
                "average_return_all": performance.average_returns.all_time_return,
                "sharpe_1d": performance.sharpe.one_day_annualized_sharpe,
                "sharpe_7d": performance.sharpe.seven_day_annualized_sharpe,
                "trades_count": performance.trades_count,
                # Source usage statistics
                "mean_google_sources": mean_google_sources,
                "median_google_sources": median_google_sources,
                "mean_webpage_sources": mean_webpage_sources,
                "median_webpage_sources": median_webpage_sources,
                "mean_total_sources": mean_total_sources,
                "median_total_sources": median_total_sources,
                "decisions_count": len(model_decisions),
            }
        )

    return pd.DataFrame(model_data)


def calculate_correlations(df):
    """Calculate correlation coefficients between sources and performance metrics."""

    correlations = {}

    # Define metric pairs to analyze (using mean and median source counts)
    metric_pairs = [
        ("mean_total_sources", "final_brier_score"),
        ("mean_total_sources", "average_return_7d"),
        ("median_total_sources", "final_brier_score"),
        ("median_total_sources", "average_return_7d"),
        ("mean_google_sources", "final_brier_score"),
        ("mean_google_sources", "average_return_7d"),
        ("median_google_sources", "final_brier_score"),
        ("median_google_sources", "average_return_7d"),
        ("mean_webpage_sources", "final_brier_score"),
        ("mean_webpage_sources", "average_return_7d"),
        ("median_webpage_sources", "final_brier_score"),
        ("median_webpage_sources", "average_return_7d"),
    ]

    for x_metric, y_metric in metric_pairs:
        # Filter out rows with missing data
        valid_data = df.dropna(subset=[x_metric, y_metric])

        if len(valid_data) > 3:  # Need sufficient data points
            # Calculate Pearson correlation
            corr_coef, p_value = stats.pearsonr(
                valid_data[x_metric], valid_data[y_metric]
            )

            correlations[f"{x_metric}_vs_{y_metric}"] = {
                "correlation": corr_coef,
                "p_value": p_value,
                "n_samples": len(valid_data),
                "significant": p_value < 0.05,
            }

    return correlations


def create_sources_vs_brier_scatter(df):
    """Create scatter plot of mean sources count vs Brier score."""

    fig = go.Figure()

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=df["mean_total_sources"],
            y=df["final_brier_score"],
            mode="markers",
            marker=dict(
                size=10,
                color=df["trades_count"],
                colorscale="Viridis",
                colorbar=dict(title="Number of Trades"),
                opacity=0.8,
                line=dict(width=1, color="black"),
            ),
            text=df["model_name"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Mean Total Sources: %{x:.1f}<br>"
                "Brier Score: %{y:.3f}<br>"
                "Trades: %{marker.color}<br>"
                "Decisions: " + df["decisions_count"].astype(str) + "<br>"
                "<extra></extra>"
            ),
            name="Models",
        )
    )

    # Add trendline
    if len(df) > 1:
        z = np.polyfit(df["mean_total_sources"], df["final_brier_score"], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(
            df["mean_total_sources"].min(), df["mean_total_sources"].max(), 100
        )
        y_trend = p(x_trend)

        fig.add_trace(
            go.Scatter(
                x=x_trend,
                y=y_trend,
                mode="lines",
                name="Trend Line",
                line=dict(color="red", dash="dash"),
            )
        )

    fig.update_layout(
        xaxis_title="Mean Total Sources Count",
        yaxis_title="Brier Score (Lower is Better)",
        height=600,
        width=800,
    )

    return fig


def create_sources_vs_returns_scatter(df):
    """Create scatter plot of mean sources count vs average returns."""

    fig = go.Figure()

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=df["mean_total_sources"],
            y=df["average_return_7d"],
            mode="markers",
            marker=dict(
                size=10,
                color="lightblue",
                opacity=0.8,
                line=dict(width=1, color="black"),
            ),
            text=df["model_name"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Mean Total Sources: %{x:.1f}<br>"
                "7d Avg Return: %{y:.3f}%<br>"
                "Trades: " + df["trades_count"].astype(str) + "<br>"
                "Decisions: " + df["decisions_count"].astype(str) + "<br>"
                "<extra></extra>"
            ),
            name="Models",
        )
    )

    # Add trendline
    if len(df) > 1:
        z = np.polyfit(df["mean_total_sources"], df["average_return_7d"], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(
            df["mean_total_sources"].min(), df["mean_total_sources"].max(), 100
        )
        y_trend = p(x_trend)

        fig.add_trace(
            go.Scatter(
                x=x_trend,
                y=y_trend,
                mode="lines",
                name="Trend Line",
                line=dict(color="red", dash="dash"),
            )
        )

    fig.update_layout(
        xaxis_title="Mean Total Sources Count",
        yaxis_title="Average Return (%)",
        height=600,
        width=800,
    )

    return fig


def create_webpage_sources_vs_returns_scatter(df):
    """Create scatter plot of mean webpage sources count vs average returns (excluding Sonar)."""

    # Exclude Sonar Deep Research to reduce outlier bias
    df_no_sonar = df[~df["model_name"].str.contains("Sonar", na=False)]

    fig = go.Figure()

    # Create selective text annotations - only for specific models
    highlight_models = ["GPT-5", "Grok 4", "DeepSeek R1", "GPT-5 Mini"]
    text_labels = []
    for model in df_no_sonar["model_name"]:
        if any(highlight in model for highlight in highlight_models):
            text_labels.append(model)
        else:
            text_labels.append("")

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=df_no_sonar["mean_webpage_sources"],
            y=df_no_sonar["average_return_7d"],
            mode="markers+text",
            text=text_labels,
            textposition="top right",
            marker=dict(size=10),
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "Mean Visited Webpages: %{x:.1f}<br>"
                "7d Avg Return: %{y:.3f}%<br>"
                "Trades: " + df_no_sonar["trades_count"].astype(str) + "<br>"
                "Decisions: " + df_no_sonar["decisions_count"].astype(str) + "<br>"
                "<extra></extra>"
            ),
            customdata=df_no_sonar[
                "model_name"
            ],  # Use customdata for hover since text is selective
            showlegend=False,
        )
    )

    # Add trendline
    if len(df_no_sonar) > 1:
        z = np.polyfit(
            df_no_sonar["mean_webpage_sources"], df_no_sonar["average_return_7d"], 1
        )
        p = np.poly1d(z)
        x_trend = np.linspace(
            df_no_sonar["mean_webpage_sources"].min(),
            df_no_sonar["mean_webpage_sources"].max(),
            100,
        )
        y_trend = p(x_trend)

        fig.add_trace(
            go.Scatter(
                x=x_trend,
                y=y_trend,
                mode="lines",
                line=dict(color="red", dash="dash"),
                showlegend=False,
            )
        )

    fig.update_layout(
        xaxis_title="Mean Visited Webpages",
        yaxis_title="Average Return (%)",
        xaxis=dict(range=[0, 1.6]),
        height=600,
        width=800,
    )

    return fig


def create_sources_breakdown_scatter(df):
    """Create scatter plot showing breakdown of mean Google vs Webpage sources."""

    fig = go.Figure()

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=df["mean_google_sources"],
            y=df["mean_webpage_sources"],
            mode="markers",
            marker=dict(
                size=12,
                color=df["average_return_7d"],
                colorscale="RdYlGn",
                cmid=0,
                colorbar=dict(title="7d Avg Return (%)"),
                opacity=0.8,
                line=dict(width=1, color="black"),
            ),
            text=df["model_name"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Mean Google Sources: %{x:.1f}<br>"
                "Mean Webpage Sources: %{y:.1f}<br>"
                "7d Avg Return: %{marker.color:.3f}%<br>"
                "Decisions: " + df["decisions_count"].astype(str) + "<br>"
                "<extra></extra>"
            ),
            name="Models",
        )
    )

    fig.update_layout(
        xaxis_title="Mean Google Sources Count",
        yaxis_title="Mean Webpage Sources Count",
        height=600,
        width=800,
    )

    return fig


def create_correlation_summary_table(correlations):
    """Create a summary table of correlations."""

    # Convert correlations dict to DataFrame for display
    correlation_rows = []
    for key, values in correlations.items():
        source_type, metric = key.split("_vs_")
        correlation_rows.append(
            {
                "Source Type": source_type.replace("_", " ").title(),
                "Performance Metric": metric.replace("_", " ").title(),
                "Correlation": f"{values['correlation']:.3f}",
                "P-Value": f"{values['p_value']:.3f}",
                "Significant": "✓" if values["significant"] else "✗",
                "Sample Size": values["n_samples"],
            }
        )

    correlation_df = pd.DataFrame(correlation_rows)

    # Create table visualization
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(correlation_df.columns),
                    fill_color="lightblue",
                    align="center",
                    font=dict(size=12, color="black"),
                ),
                cells=dict(
                    values=[correlation_df[col] for col in correlation_df.columns],
                    fill_color="white",
                    align="center",
                    font=dict(size=11),
                ),
            )
        ]
    )

    fig.update_layout(height=400, width=800)

    return fig


def main():
    print("Loading backend data...")
    backend_data = get_data_for_backend()

    print("Extracting model-level data...")
    df = extract_model_level_data(backend_data)

    if df.empty:
        print("No model data found!")
        return

    # Filter out baseline models
    baseline_keywords = ["baseline", "random", "most_likely"]
    df_filtered = df[
        ~df["model_name"]
        .str.lower()
        .str.contains("|".join(baseline_keywords), na=False)
    ]

    print(
        f"Analyzing {len(df_filtered)} models (filtered out {len(df) - len(df_filtered)} baselines)..."
    )

    print("\nModel-level summary:")
    print(
        df_filtered[
            [
                "model_name",
                "mean_total_sources",
                "median_total_sources",
                "final_brier_score",
                "average_return_7d",
                "decisions_count",
            ]
        ].to_string()
    )

    print("\nCalculating correlations...")
    correlations = calculate_correlations(df_filtered)

    print("\nCorrelation Results:")
    for key, values in correlations.items():
        print(
            f"{key}: r={values['correlation']:.3f}, p={values['p_value']:.3f} ({'significant' if values['significant'] else 'not significant'})"
        )

    # Create output directory for this study in parent /analyses folder
    study_name = "sources_vs_performance_analysis"
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "predibench-frontend-react/public" / study_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nCreating visualizations in {output_dir}...")

    # 1. Sources vs Brier Score
    print("Creating sources vs Brier score plot...")
    fig1 = create_sources_vs_brier_scatter(df_filtered)
    apply_template(fig1)
    fig1.write_json(output_dir / "sources_vs_brier_score.json")

    # 2. Sources vs Returns
    print("Creating sources vs returns plot...")
    fig2 = create_sources_vs_returns_scatter(df_filtered)
    apply_template(fig2)
    fig2.write_json(output_dir / "sources_vs_returns.json")

    # 3. Webpage Sources vs Returns
    print("Creating webpage sources vs returns plot...")
    fig3 = create_webpage_sources_vs_returns_scatter(df_filtered)
    apply_template(fig3)
    fig3.write_json(output_dir / "webpage_sources_vs_returns.json")

    # 4. Sources breakdown
    print("Creating sources breakdown plot...")
    fig4 = create_sources_breakdown_scatter(df_filtered)
    apply_template(fig4)
    fig4.write_json(output_dir / "google_vs_webpage_sources.json")

    # 5. Correlation summary table
    print("Creating correlation summary table...")
    fig5 = create_correlation_summary_table(correlations)
    apply_template(fig5)
    fig5.write_json(output_dir / "correlation_summary.json")

    print(f"\nAnalysis complete! Files saved to {output_dir}")
    print("Generated files:")
    print("- sources_vs_brier_score.html")
    print("- sources_vs_returns.html")
    print("- webpage_sources_vs_returns.html")
    print("- google_vs_webpage_sources.html")
    print("- correlation_summary.html")


if __name__ == "__main__":
    main()
