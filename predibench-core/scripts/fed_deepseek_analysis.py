#!/usr/bin/env python3
"""
Fed Event Analysis with DeepSeek - Individual Model Analysis
"""

import json
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from predibench.utils import apply_template
from predibench.logger_config import get_logger
from predibench.common import FRONTEND_PUBLIC_PATH

logger = get_logger(__name__)

# Configuration for DeepSeek
RESULTS_BASE_PATH = "/Users/charlesazam/charloupioupiou/market-bench/bucket-prod/model_results/2025-09-21"
OUTPUT_BASE_PATH = "/Users/charlesazam/charloupioupiou/market-bench/analyses/llm_distribution_study"

DEEPSEEK_CONFIG = {
    "deepseek-ai--DeepSeek-V3.1": {
        "name": "DeepSeek V3.1",
        "runs": list(range(22)),  # 0 to 21
        "color": "#2ca02c"
    }
}

FED_EVENT_ID = "27824"

# Market prices - at decision time and current with short names and outcomes
MARKET_PRICES = {
    "Fed decreases interest rates by 25 bps after October 2025 meeting?": {
        "decision_time_price": 0.785,
        "current_price": 0.86,
        "short_name": "25 bps Cut",
        "actual_outcome": "TBD"
    },
    "Fed decreases interest rates by 50+ bps after October 2025 meeting?": {
        "decision_time_price": 0.0735,
        "current_price": 0.042,
        "short_name": "50+ bps Cut",
        "actual_outcome": "TBD"
    },
    "No change in Fed interest rates after October 2025 meeting?": {
        "decision_time_price": 0.145,
        "current_price": 0.11,
        "short_name": "No Change",
        "actual_outcome": "TBD"
    },
    "Fed increases interest rates by 25+ bps after October 2025 meeting?": {
        "decision_time_price": 0.0075,
        "current_price": 0.00,
        "short_name": "25+ bps Increase",
        "actual_outcome": "TBD"
    }
}

def calculate_returns(bet_amount, decision_price, current_price):
    """Calculate hypothetical returns based on price movement."""
    if bet_amount == 0:
        return 0

    price_change = current_price - decision_price

    if bet_amount > 0:  # Long position
        return bet_amount * (price_change / decision_price)
    else:  # Short position
        return abs(bet_amount) * (-price_change / decision_price)

def load_model_data(model_id: str, run_indices: list) -> list:
    """Load all runs for a specific model."""
    results_path = Path(RESULTS_BASE_PATH)
    all_runs = []

    for run_idx in run_indices:
        run_path = results_path / f"{model_id}_run_{run_idx}" / "model_investment_decisions.json"
        if run_path.exists():
            try:
                with open(run_path, 'r') as f:
                    data = json.load(f)
                    data['run_index'] = run_idx
                    all_runs.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {run_path}: {e}")

    return all_runs

def extract_fed_data(all_runs: list, model_name: str) -> pd.DataFrame:
    """Extract Fed event data from all runs with returns calculation."""
    fed_decisions = []

    for run_data in all_runs:
        run_idx = run_data['run_index']

        for event in run_data['event_investment_decisions']:
            if event['event_id'] == FED_EVENT_ID:
                for market in event['market_investment_decisions']:
                    decision = market['decision']
                    market_question = market['market_question']

                    # Calculate returns if market price data available
                    returns = 0
                    if market_question in MARKET_PRICES:
                        decision_price = MARKET_PRICES[market_question]["decision_time_price"]
                        current_price = MARKET_PRICES[market_question]["current_price"]
                        returns = calculate_returns(decision['bet'], decision_price, current_price)

                    # Determine bet direction outcome
                    bet_direction = "None"
                    if decision['bet'] > 0:
                        bet_direction = "Long"
                    elif decision['bet'] < 0:
                        bet_direction = "Short"

                    # Include all decisions for Fed event
                    market_data = {
                        'run_index': run_idx,
                        'model': model_name,
                        'market_id': market['market_id'],
                        'market_question': market_question,
                        'estimated_probability': decision['estimated_probability'],
                        'bet': decision['bet'],
                        'confidence': decision['confidence'],
                        'rationale': decision['rationale'],
                        'returns': returns,
                        'bet_direction': bet_direction
                    }

                    fed_decisions.append(market_data)

    return pd.DataFrame(fed_decisions)

def create_deepseek_individual_analysis():
    """Create readable individual model analysis for DeepSeek."""
    output_path = Path(OUTPUT_BASE_PATH)

    # Load data for DeepSeek
    model_id = "deepseek-ai--DeepSeek-V3.1"
    config = DEEPSEEK_CONFIG[model_id]

    all_runs = load_model_data(model_id, config['runs'])
    if not all_runs:
        logger.error("No DeepSeek data found")
        return

    fed_df = extract_fed_data(all_runs, config['name'])
    if fed_df.empty:
        logger.error("No Fed event data found for DeepSeek")
        return

    markets = sorted(fed_df['market_question'].unique())
    model_name = config['name']

    # Create 4x3 grid: 4 markets (rows) x 3 metrics (columns)
    fig = make_subplots(
        rows=4, cols=3,
        subplot_titles=[
            'Estimated Probability', 'Bet Amount', 'Confidence',
            '', '', '',  # Empty titles for remaining rows
            '', '', '',
            '', '', ''
        ],
        vertical_spacing=0.08,
        horizontal_spacing=0.15,
        row_titles=[MARKET_PRICES[market]["short_name"] for market in markets],
        specs=[[{"type": "xy"} for _ in range(3)] for _ in range(4)]
    )

    # Market colors
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    # Process each market (each gets its own row)
    for market_idx, market in enumerate(markets):
        market_subset = fed_df[fed_df['market_question'] == market]
        color = colors[market_idx]

        # Column 1: Estimated Probability with individual points
        fig.add_trace(
            go.Box(
                y=market_subset['estimated_probability'],
                name=MARKET_PRICES[market]["short_name"],
                marker_color=color,
                showlegend=False,
                boxpoints='all',  # Show all individual points
                jitter=0.3,
                pointpos=0,
                width=0.6,
                opacity=0.7
            ),
            row=market_idx + 1, col=1
        )

        # Add decision time market price line only
        if market in MARKET_PRICES:
            # Decision time price (THICK red solid) - no annotation
            fig.add_hline(
                y=MARKET_PRICES[market]["decision_time_price"],
                line=dict(color="red", width=4, dash="solid"),
                row=market_idx + 1, col=1
            )

        # Column 2: Bet Amount with color-coded points by direction
        # Create separate traces for Long/Short/None bets
        long_bets = market_subset[market_subset['bet_direction'] == 'Long']
        short_bets = market_subset[market_subset['bet_direction'] == 'Short']
        no_bets = market_subset[market_subset['bet_direction'] == 'None']

        # Box plot for all bets
        fig.add_trace(
            go.Box(
                y=market_subset['bet'],
                name=MARKET_PRICES[market]["short_name"],
                marker_color=color,
                showlegend=False,
                boxpoints=False,
                width=0.4,
                opacity=0.5
            ),
            row=market_idx + 1, col=2
        )

        # Add colored scatter points for bet directions
        if not long_bets.empty:
            fig.add_trace(
                go.Scatter(
                    x=[0] * len(long_bets),
                    y=long_bets['bet'],
                    mode='markers',
                    marker=dict(color='green', size=6, symbol='triangle-up'),
                    name='Long' if market_idx == 0 else None,
                    showlegend=(market_idx == 0),
                    hovertemplate='Long bet: %{y:.2f}<extra></extra>'
                ),
                row=market_idx + 1, col=2
            )

        if not short_bets.empty:
            fig.add_trace(
                go.Scatter(
                    x=[0] * len(short_bets),
                    y=short_bets['bet'],
                    mode='markers',
                    marker=dict(color='red', size=6, symbol='triangle-down'),
                    name='Short' if market_idx == 0 else None,
                    showlegend=(market_idx == 0),
                    hovertemplate='Short bet: %{y:.2f}<extra></extra>'
                ),
                row=market_idx + 1, col=2
            )

        if not no_bets.empty:
            fig.add_trace(
                go.Scatter(
                    x=[0] * len(no_bets),
                    y=no_bets['bet'],
                    mode='markers',
                    marker=dict(color='gray', size=6, symbol='circle'),
                    name='No Bet' if market_idx == 0 else None,
                    showlegend=(market_idx == 0),
                    hovertemplate='No bet: %{y:.2f}<extra></extra>'
                ),
                row=market_idx + 1, col=2
            )

        # Add zero line for bet amounts
        fig.add_hline(
            y=0,
            line=dict(color="black", width=2, dash="solid"),
            annotation_text="No Bet",
            annotation_position="top right",
            row=market_idx + 1, col=2
        )

        # Column 3: Confidence with individual points
        fig.add_trace(
            go.Box(
                y=market_subset['confidence'],
                name=MARKET_PRICES[market]["short_name"],
                marker_color=color,
                showlegend=False,
                boxpoints='all',
                jitter=0.3,
                pointpos=0,
                width=0.6,
                opacity=0.7
            ),
            row=market_idx + 1, col=3
        )

    # Update layout
    fig.update_layout(
        height=800,
        width=1200,
        showlegend=False,
        font=dict(size=10)
    )

    # Set axis ranges and remove tick labels for cleaner look
    for market_idx in range(4):
        # Probability column: 0-1 range
        fig.update_yaxes(range=[0, 1.05], row=market_idx + 1, col=1)
        fig.update_xaxes(showticklabels=False, row=market_idx + 1, col=1)

        # Bet amount column: auto range
        fig.update_xaxes(showticklabels=False, row=market_idx + 1, col=2)

        # Confidence column: 0-10 range
        fig.update_yaxes(range=[0, 10.5], row=market_idx + 1, col=3)
        fig.update_xaxes(showticklabels=False, row=market_idx + 1, col=3)

    # Apply template
    apply_template(fig, width=1200, height=800)
    fig.update_layout(width=1400, height=900)

    safe_model_name = model_name.replace(' ', '_').replace('/', '-').replace('.', '_')
    fig.write_html(output_path / f"fed_readable_{safe_model_name}.html")

    # Save JSON to frontend public path
    fig.write_json(FRONTEND_PUBLIC_PATH / f"fed_readable_{safe_model_name}.json")

    logger.info(f"DeepSeek Fed analysis saved for {model_name}")

def main():
    """Run the DeepSeek Fed event analysis."""
    logger.info("Creating DeepSeek Fed Event Analysis...")

    # Create individual model analysis for DeepSeek
    create_deepseek_individual_analysis()

    logger.info("DeepSeek Fed analysis complete!")
    logger.info("Generated files:")
    logger.info("- fed_readable_DeepSeek_V3_1.html")
    logger.info("- fed_readable_DeepSeek_V3_1.json (saved to frontend public path)")

if __name__ == "__main__":
    main()