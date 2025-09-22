#!/usr/bin/env python3
"""
Fed Event Readable Analysis - Clean, Non-overlapping Visualizations
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from predibench.common import (
    DATA_PATH,
    FRONTEND_PUBLIC_PATH,
    PREFIX_MODEL_RESULTS,
)
from predibench.logger_config import get_logger
from predibench.utils import apply_template

logger = get_logger(__name__)


def _get_latest_results_base_path() -> Path:
    """Return the latest date folder under bucket-prod/model_results."""
    base = DATA_PATH / PREFIX_MODEL_RESULTS
    if not base.exists():
        logger.error("Results base path does not exist: %s", base)
        return base

    date_dirs = [d for d in base.iterdir() if d.is_dir()]
    if not date_dirs:
        logger.error("No date directories found under: %s", base)
        return base

    def parse_date(p: Path) -> datetime:
        try:
            return datetime.strptime(p.name, "%Y-%m-%d")
        except Exception:
            # If non-date directories exist, push them to the beginning
            return datetime.min

    latest = max(date_dirs, key=parse_date)
    return latest


# Configuration (auto-detected latest results date directory)
RESULTS_BASE_PATH = _get_latest_results_base_path()

MODELS_CONFIG = {
    "Qwen--Qwen3-Coder-480B-A35B-Instruct": {
        "name": "QWEN 480B",
        "runs": list(range(32)),
        "color": "#1f77b4",
    },
    "openai--gpt-oss-120b": {
        "name": "GPT OSS 120B",
        "runs": list(range(28)),
        "color": "#ff7f0e",
    },
}

FED_EVENT_ID = "27824"

# Market prices - at decision time and current with short names and outcomes
MARKET_PRICES = {
    "Fed decreases interest rates by 25 bps after October 2025 meeting?": {
        "decision_time_price": 0.785,
        "current_price": 0.86,
        "short_name": "25 bps Cut",
        "actual_outcome": "TBD",  # Will be determined by Fed meeting
    },
    "Fed decreases interest rates by 50+ bps after October 2025 meeting?": {
        "decision_time_price": 0.0735,
        "current_price": 0.042,
        "short_name": "50+ bps Cut",
        "actual_outcome": "TBD",
    },
    "No change in Fed interest rates after October 2025 meeting?": {
        "decision_time_price": 0.145,
        "current_price": 0.11,
        "short_name": "No Change",
        "actual_outcome": "TBD",
    },
    "Fed increases interest rates by 25+ bps after October 2025 meeting?": {
        "decision_time_price": 0.0075,
        "current_price": 0.00,
        "short_name": "25+ bps Increase",
        "actual_outcome": "TBD",
    },
}


# For returns calculation, we'll use current price movement as proxy
# Positive bet = buying "Yes", Negative bet = buying "No"
def calculate_returns(bet_amount, decision_price, current_price):
    """Calculate hypothetical returns based on price movement."""
    if bet_amount == 0:
        return 0

    # Price movement from decision time to current
    price_change = current_price - decision_price

    # If betting "Yes" (positive bet) and price increased, profit
    # If betting "No" (negative bet) and price decreased, profit
    if bet_amount > 0:  # Long position
        return bet_amount * (price_change / decision_price)
    else:  # Short position
        return abs(bet_amount) * (-price_change / decision_price)


def load_model_data(model_id: str, run_indices: list) -> list:
    """Load all runs for a specific model."""
    results_path = RESULTS_BASE_PATH
    all_runs = []

    for run_idx in run_indices:
        run_path = (
            results_path
            / f"{model_id}_run_{run_idx}"
            / "model_investment_decisions.json"
        )
        if run_path.exists():
            try:
                with open(run_path, "r") as f:
                    data = json.load(f)
                    data["run_index"] = run_idx
                    all_runs.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {run_path}: {e}")

    return all_runs


def extract_fed_data(all_runs: list, model_name: str) -> pd.DataFrame:
    """Extract Fed event data from all runs with returns calculation."""
    fed_decisions = []

    for run_data in all_runs:
        run_idx = run_data["run_index"]

        for event in run_data["event_investment_decisions"]:
            if event["event_id"] == FED_EVENT_ID:
                for market in event["market_investment_decisions"]:
                    decision = market["decision"]
                    market_question = market["market_question"]

                    # Calculate returns if market price data available
                    returns = 0
                    if market_question in MARKET_PRICES:
                        decision_price = MARKET_PRICES[market_question][
                            "decision_time_price"
                        ]
                        current_price = MARKET_PRICES[market_question]["current_price"]
                        returns = calculate_returns(
                            decision["bet"], decision_price, current_price
                        )

                    # Determine bet direction outcome
                    bet_direction = "None"
                    if decision["bet"] > 0:
                        bet_direction = "Long"
                    elif decision["bet"] < 0:
                        bet_direction = "Short"

                    # Include all decisions for Fed event
                    market_data = {
                        "run_index": run_idx,
                        "model": model_name,
                        "market_id": market["market_id"],
                        "market_question": market_question,
                        "estimated_probability": decision["estimated_probability"],
                        "bet": decision["bet"],
                        "confidence": decision["confidence"],
                        "rationale": decision["rationale"],
                        "returns": returns,
                        "bet_direction": bet_direction,
                    }

                    fed_decisions.append(market_data)

    return pd.DataFrame(fed_decisions)


def create_readable_individual_analysis():
    """Create readable individual model analysis with proper spacing."""
    repo_root = Path(__file__).resolve().parents[3]
    html_out_dir = repo_root / "analyses/fed_event_analysis_readable"
    html_out_dir.mkdir(parents=True, exist_ok=True)

    json_out_dir = FRONTEND_PUBLIC_PATH / "fed_event_analysis_readable"
    json_out_dir.mkdir(parents=True, exist_ok=True)

    # Load data for both models
    all_fed_data = []

    for model_id, config in MODELS_CONFIG.items():
        all_runs = load_model_data(model_id, config["runs"])
        if all_runs:
            fed_df = extract_fed_data(all_runs, config["name"])
            if not fed_df.empty:
                all_fed_data.append(fed_df)

    if not all_fed_data:
        logger.error("No Fed event data found")
        return

    # Combine all Fed data
    combined_fed_df = pd.concat(all_fed_data, ignore_index=True)
    markets = sorted(combined_fed_df["market_question"].unique())

    # Create separate plots for each model with GRID LAYOUT
    for model_name in combined_fed_df["model"].unique():
        model_data = combined_fed_df[combined_fed_df["model"] == model_name]

        # Create 4x2 grid: 4 markets (rows) x 2 metrics (columns)
        fig = make_subplots(
            rows=4,
            cols=2,
            subplot_titles=[
                "Estimated Probability",
                "Bet Amount",
                "",
                "",  # Empty titles for remaining rows
                "",
                "",
                "",
                "",
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.20,
            row_titles=[MARKET_PRICES[market]["short_name"] for market in markets],
            specs=[[{"type": "xy"} for _ in range(2)] for _ in range(4)],
        )

        # Market colors
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

        # Process each market (each gets its own row)
        for market_idx, market in enumerate(markets):
            market_subset = model_data[model_data["market_question"] == market]
            color = colors[market_idx]

            # Column 1: Estimated Probability with individual points
            fig.add_trace(
                go.Box(
                    y=market_subset["estimated_probability"],
                    name=MARKET_PRICES[market]["short_name"],
                    marker_color=color,
                    showlegend=False,
                    boxpoints="all",  # Show all individual points
                    jitter=0.3,
                    pointpos=0,
                    width=0.6,
                    opacity=0.7,
                ),
                row=market_idx + 1,
                col=1,
            )

            # Add decision time market price line only
            if market in MARKET_PRICES:
                # Decision time price (THICK red solid) - no annotation
                fig.add_hline(
                    y=MARKET_PRICES[market]["decision_time_price"],
                    line=dict(color="red", width=4, dash="solid"),
                    row=market_idx + 1,
                    col=1,
                )

            # Column 2: Bet Amount with color-coded points by direction
            # Create separate traces for Long/Short/None bets
            long_bets = market_subset[market_subset["bet_direction"] == "Long"]
            short_bets = market_subset[market_subset["bet_direction"] == "Short"]
            no_bets = market_subset[market_subset["bet_direction"] == "None"]

            # Box plot for all bets
            fig.add_trace(
                go.Box(
                    y=market_subset["bet"],
                    name=MARKET_PRICES[market]["short_name"],
                    marker_color=color,
                    showlegend=False,
                    boxpoints=False,
                    width=0.4,
                    opacity=0.5,
                ),
                row=market_idx + 1,
                col=2,
            )

            # Add colored scatter points for bet directions
            if not long_bets.empty:
                fig.add_trace(
                    go.Scatter(
                        x=[0] * len(long_bets),
                        y=long_bets["bet"],
                        mode="markers",
                        marker=dict(color="green", size=6, symbol="triangle-up"),
                        name="Long" if market_idx == 0 else None,
                        showlegend=(market_idx == 0),
                        hovertemplate="Long bet: %{y:.2f}<extra></extra>",
                    ),
                    row=market_idx + 1,
                    col=2,
                )

            if not short_bets.empty:
                fig.add_trace(
                    go.Scatter(
                        x=[0] * len(short_bets),
                        y=short_bets["bet"],
                        mode="markers",
                        marker=dict(color="red", size=6, symbol="triangle-down"),
                        name="Short" if market_idx == 0 else None,
                        showlegend=(market_idx == 0),
                        hovertemplate="Short bet: %{y:.2f}<extra></extra>",
                    ),
                    row=market_idx + 1,
                    col=2,
                )

            if not no_bets.empty:
                fig.add_trace(
                    go.Scatter(
                        x=[0] * len(no_bets),
                        y=no_bets["bet"],
                        mode="markers",
                        marker=dict(color="gray", size=6, symbol="circle"),
                        name="No Bet" if market_idx == 0 else None,
                        showlegend=(market_idx == 0),
                        hovertemplate="No bet: %{y:.2f}<extra></extra>",
                    ),
                    row=market_idx + 1,
                    col=2,
                )

            # Add zero line for bet amounts
            fig.add_hline(
                y=0,
                line=dict(color="black", width=2, dash="solid"),
                annotation_text="No Bet",
                annotation_position="top right",
                row=market_idx + 1,
                col=2,
            )

        # Update layout
        fig.update_layout(height=1200, width=1800, showlegend=False, font=dict(size=12))

        # Set axis ranges and remove tick labels for cleaner look
        for market_idx in range(4):
            # Probability column: 0-1 range
            fig.update_yaxes(range=[0, 1.05], row=market_idx + 1, col=1)
            fig.update_xaxes(showticklabels=False, row=market_idx + 1, col=1)

            # Bet amount column: auto range
            fig.update_xaxes(showticklabels=False, row=market_idx + 1, col=2)

        # Apply template
        apply_template(fig, width=1800, height=1200)
        fig.update_layout(width=2000, height=1400)

        safe_model_name = model_name.replace(" ", "_").replace("/", "-")
        html_path = (html_out_dir / f"fed_readable_{safe_model_name}.html").resolve()
        fig.write_html(str(html_path))

        # Save JSON to frontend public path
        json_path = (json_out_dir / f"fed_readable_{safe_model_name}.json").resolve()
        fig.write_json(str(json_path))

        logger.info(f"Readable Fed analysis saved for {model_name}")


def create_readable_comparative_analysis():
    """Create readable comparative analysis with short market names."""
    repo_root = Path(__file__).resolve().parents[3]
    html_out_dir = repo_root / "analyses/fed_event_analysis_readable"
    html_out_dir.mkdir(parents=True, exist_ok=True)

    json_out_dir = FRONTEND_PUBLIC_PATH / "fed_event_analysis_readable"
    json_out_dir.mkdir(parents=True, exist_ok=True)

    # Load data for both models
    all_fed_data = []

    for model_id, config in MODELS_CONFIG.items():
        all_runs = load_model_data(model_id, config["runs"])
        if all_runs:
            fed_df = extract_fed_data(all_runs, config["name"])
            if not fed_df.empty:
                all_fed_data.append(fed_df)

    if len(all_fed_data) < 2:
        logger.error("Need both models for comparative analysis")
        return

    # Combine all Fed data
    combined_fed_df = pd.concat(all_fed_data, ignore_index=True)
    markets = sorted(combined_fed_df["market_question"].unique())

    # Create comparative subplot with SHORT NAMES
    short_names = [MARKET_PRICES[market]["short_name"] for market in markets]

    fig = make_subplots(
        rows=2,
        cols=4,
        subplot_titles=short_names,  # Only first row gets titles
        vertical_spacing=0.20,
        horizontal_spacing=0.10,
        specs=[[{"type": "xy"} for _ in range(4)] for _ in range(2)],
    )

    # Add y-axis titles on the left side
    fig.update_yaxes(title_text="Estimated Probability", row=1, col=1)
    fig.update_yaxes(title_text="Bet Amount", row=2, col=1)

    model_colors = {"QWEN 480B": "#1f77b4", "GPT OSS 120B": "#ff7f0e"}

    # For each market (column) and metric (row)
    for col_idx, market in enumerate(markets):
        market_data = combined_fed_df[combined_fed_df["market_question"] == market]

        for model_name in market_data["model"].unique():
            model_subset = market_data[market_data["model"] == model_name]
            color = model_colors.get(model_name, "gray")

            # Row 1: Estimated Probability
            fig.add_trace(
                go.Box(
                    y=model_subset["estimated_probability"],
                    name=model_name,
                    marker_color=color,
                    showlegend=(col_idx == 0),  # Only show legend in first column
                    opacity=0.8,
                    boxpoints="all",  # Show all individual points
                    jitter=0.3,
                    pointpos=0,
                    width=0.4,
                ),
                row=1,
                col=col_idx + 1,
            )

            # Row 2: Bet Amount
            fig.add_trace(
                go.Box(
                    y=model_subset["bet"],
                    name=model_name,
                    marker_color=color,
                    showlegend=False,
                    opacity=0.8,
                    boxpoints="all",  # Show all individual points
                    jitter=0.3,
                    pointpos=0,
                    width=0.4,
                ),
                row=2,
                col=col_idx + 1,
            )

        # Add market price lines to probability plots (row 1)
        if market in MARKET_PRICES:
            # Decision time price only (red solid)
            fig.add_hline(
                y=MARKET_PRICES[market]["decision_time_price"],
                line=dict(color="gray", width=2, dash="solid"),
                row=1,
                col=col_idx + 1,
                text=MARKET_PRICES[market]["short_name"],
            )

        # Add zero line for bet amounts (row 2)
        fig.add_hline(
            y=0, line=dict(color="gray", width=1, dash="dot"), row=2, col=col_idx + 1
        )

    # Update layout
    fig.update_layout(
        height=600,
        width=800,
        showlegend=False,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=-0.12,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
    )

    # Set consistent y-axis ranges
    for col in range(1, 5):  # 4 markets
        fig.update_yaxes(range=[0, 1.05], row=1, col=col)  # Probability
        fig.update_yaxes(range=[-0.5, 0.5], row=2, col=col)  # Bets

        # Bet amounts keep auto range

    # Remove x-axis labels for cleaner look
    for row in range(1, 3):
        for col in range(1, 5):
            fig.update_xaxes(showticklabels=False, row=row, col=col)

    # Apply template
    apply_template(fig, width=800, height=600)

    html_path = (html_out_dir / "fed_readable_comparative.html").resolve()
    fig.write_html(str(html_path))

    # Save JSON to frontend public path
    json_path = (json_out_dir / "fed_readable_comparative.json").resolve()
    fig.write_json(str(json_path))

    logger.info("Readable comparative Fed analysis saved  in json under %s", html_path)
    logger.info("Readable comparative Fed analysis saved in html under %s", json_path)


def create_returns_analysis():
    """Create returns analysis showing actual P&L from bets."""
    repo_root = Path(__file__).resolve().parents[3]
    html_out_dir = repo_root / "analyses/fed_event_analysis_readable"
    html_out_dir.mkdir(parents=True, exist_ok=True)

    json_out_dir = FRONTEND_PUBLIC_PATH / "fed_event_analysis_readable"
    json_out_dir.mkdir(parents=True, exist_ok=True)

    # Load data for both models
    all_fed_data = []

    for model_id, config in MODELS_CONFIG.items():
        all_runs = load_model_data(model_id, config["runs"])
        if all_runs:
            fed_df = extract_fed_data(all_runs, config["name"])
            if not fed_df.empty:
                all_fed_data.append(fed_df)

    if not all_fed_data:
        logger.error("No Fed event data found for returns analysis")
        return

    # Combine all Fed data
    combined_fed_df = pd.concat(all_fed_data, ignore_index=True)
    markets = sorted(combined_fed_df["market_question"].unique())

    # Create returns analysis figure
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["Returns Distribution by Model", "Returns by Market and Model"],
        specs=[[{"type": "xy"}, {"type": "xy"}]],
    )

    model_colors = {"QWEN 480B": "#1f77b4", "GPT OSS 120B": "#ff7f0e"}

    # 1. Returns distribution by model
    for model_name in combined_fed_df["model"].unique():
        model_data = combined_fed_df[combined_fed_df["model"] == model_name]
        color = model_colors.get(model_name, "gray")

        fig.add_trace(
            go.Box(
                y=model_data["returns"],
                name=model_name,
                marker_color=color,
                showlegend=True,
                boxpoints="all",
                jitter=0.3,
                pointpos=0,
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

    # Add zero line
    fig.add_hline(y=0, line=dict(color="black", width=1, dash="dash"), row=1, col=1)

    # 2. Returns by market and model
    for model_idx, model_name in enumerate(combined_fed_df["model"].unique()):
        model_data = combined_fed_df[combined_fed_df["model"] == model_name]

        for market_idx, market in enumerate(markets):
            market_data = model_data[model_data["market_question"] == market]
            short_name = MARKET_PRICES[market]["short_name"]

            if not market_data.empty:
                x_pos = market_idx + (model_idx * 0.4 - 0.2)  # Offset for side-by-side

                fig.add_trace(
                    go.Box(
                        y=market_data["returns"],
                        name=f"{model_name} - {short_name}",
                        marker_color=model_colors[model_name],
                        showlegend=False,
                        boxpoints="outliers",
                        width=0.3,
                        opacity=0.7,
                        x=[x_pos] * len(market_data),
                    ),
                    row=1,
                    col=2,
                )

    # Update x-axis for market plot
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(len(markets))),
        ticktext=[MARKET_PRICES[market]["short_name"] for market in markets],
        row=1,
        col=2,
    )
    fig.add_hline(y=0, line=dict(color="black", width=1, dash="dash"), row=1, col=2)

    # Update layout
    fig.update_layout(
        height=600,
        width=800,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=-0.10,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
    )

    # Update axis labels
    fig.update_yaxes(title_text="Returns", row=1, col=1)
    fig.update_yaxes(title_text="Returns", row=1, col=2)

    fig.update_xaxes(title_text="Model", row=1, col=1)
    fig.update_xaxes(title_text="Market", row=1, col=2)

    # Apply template
    apply_template(fig, width=800, height=600)

    html_path = (html_out_dir / "fed_returns_analysis.html").resolve()
    fig.write_html(str(html_path))

    # Save JSON to frontend public path
    json_path = (json_out_dir / "fed_returns_analysis.json").resolve()
    fig.write_json(str(json_path))

    logger.info("Fed returns analysis saved")

    # Generate returns summary statistics
    returns_summary = {}
    for model_name in combined_fed_df["model"].unique():
        model_data = combined_fed_df[combined_fed_df["model"] == model_name]

        returns_summary[model_name] = {
            "total_return": float(model_data["returns"].sum()),
            "mean_return": float(model_data["returns"].mean()),
            "median_return": float(model_data["returns"].median()),
            "std_return": float(model_data["returns"].std()),
            "positive_returns": int((model_data["returns"] > 0).sum()),
            "negative_returns": int((model_data["returns"] < 0).sum()),
            "zero_returns": int((model_data["returns"] == 0).sum()),
            "best_return": float(model_data["returns"].max()),
            "worst_return": float(model_data["returns"].min()),
        }

    summary_path = (html_out_dir / "fed_returns_summary.json").resolve()
    with open(summary_path, "w") as f:
        json.dump(returns_summary, f, indent=2)

    logger.info("Fed returns summary saved")


def main():
    """Run the readable Fed event analysis."""
    create_readable_individual_analysis()

    create_readable_comparative_analysis()

    create_returns_analysis()


if __name__ == "__main__":
    main()
