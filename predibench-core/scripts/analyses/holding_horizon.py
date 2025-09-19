#!/usr/bin/env python3
"""
Holding Horizon Analysis - Analyzing optimal holding periods for model predictions.

This script analyzes how different holding horizons (1, 2, 3, 5, 7, 10, 14, 30 days)
affect model performance by computing average returns at different time horizons.
"""

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Import predibench modules
from predibench.backend.data_loader import (
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.pnl import get_market_prices_dataframe
from predibench.logger_config import get_logger
from predibench.utils import _to_date_index, apply_template

logger = get_logger(__name__)


def compute_returns_at_horizon_using_real_system(
    model_decisions, prices_df, horizon_days
):
    """
    Compute average returns using the SAME methodology as the actual backend system.
    This matches exactly how DecisionReturns.two_day_return etc are computed.

    Args:
        model_decisions: List of ModelInvestmentDecisions
        prices_df: DataFrame with market prices over time
        horizon_days: Number of days to hold positions

    Returns:
        dict: Model ID -> average return at horizon
    """
    # Import the actual computation function
    from predibench.backend.compute_profits import compute_performance_per_decision

    # Get all unique model IDs
    all_model_ids_names = set((d.model_id, d.model_id) for d in model_decisions)

    # Run the REAL computation to get properly calculated returns
    enriched_decisions, summary_info = compute_performance_per_decision(
        all_model_ids_names, model_decisions, prices_df
    )

    # Extract the specific horizon returns from the enriched decisions
    returns_by_model = {}

    for model_decision in enriched_decisions:
        model_id = model_decision.model_id
        if model_id not in returns_by_model:
            returns_by_model[model_id] = []

        # Aggregate event-level returns for this decision
        decision_return = 0.0

        for event_decision in model_decision.event_investment_decisions:
            if event_decision.returns is not None:
                if horizon_days == 1:
                    decision_return += event_decision.returns.one_day_return
                elif horizon_days == 2:
                    decision_return += event_decision.returns.two_day_return
                elif horizon_days == 7:
                    decision_return += event_decision.returns.seven_day_return
                else:
                    # For other horizons, we need to compute from individual market decisions
                    event_return = 0.0
                    for market_decision in event_decision.market_investment_decisions:
                        if market_decision.returns is not None:
                            if horizon_days == 3:
                                # Use a custom calculation for 3-day
                                decision_date = model_decision.target_date
                                target_date = decision_date + timedelta(
                                    days=horizon_days
                                )

                                if market_decision.market_id in prices_df.columns:
                                    market_series = prices_df[
                                        market_decision.market_id
                                    ].copy()
                                    if decision_date in market_series.index:
                                        price_at_decision = market_series.loc[
                                            decision_date
                                        ]
                                        if (
                                            not pd.isna(price_at_decision)
                                            and price_at_decision != 0
                                        ):
                                            # Apply bet direction
                                            if market_decision.decision.bet < 0:
                                                signed_price_at_decision = (
                                                    1 - price_at_decision
                                                )
                                                signed_market_series = 1 - market_series
                                            else:
                                                signed_price_at_decision = (
                                                    price_at_decision
                                                )
                                                signed_market_series = market_series

                                            # Get price at horizon
                                            future_prices = signed_market_series.loc[
                                                signed_market_series.index
                                                >= target_date
                                            ]
                                            if future_prices.empty:
                                                price_at_horizon = (
                                                    signed_market_series.dropna().iloc[
                                                        -1
                                                    ]
                                                )
                                            else:
                                                price_at_horizon = (
                                                    future_prices.dropna().iloc[0]
                                                    if not future_prices.dropna().empty
                                                    else signed_market_series.dropna().iloc[
                                                        -1
                                                    ]
                                                )

                                            if not pd.isna(price_at_horizon):
                                                market_return = (
                                                    price_at_horizon
                                                    / signed_price_at_decision
                                                    - 1
                                                ) * abs(market_decision.decision.bet)
                                                event_return += market_return
                            # Add similar logic for other horizons (5, 10, 14, 21, 30)
                            elif horizon_days in [5, 10, 14, 21, 30]:
                                # Custom calculation for these horizons
                                decision_date = model_decision.target_date
                                target_date = decision_date + timedelta(
                                    days=horizon_days
                                )

                                if market_decision.market_id in prices_df.columns:
                                    market_series = prices_df[
                                        market_decision.market_id
                                    ].copy()
                                    if decision_date in market_series.index:
                                        price_at_decision = market_series.loc[
                                            decision_date
                                        ]
                                        if (
                                            not pd.isna(price_at_decision)
                                            and price_at_decision != 0
                                        ):
                                            # Apply bet direction
                                            if market_decision.decision.bet < 0:
                                                signed_price_at_decision = (
                                                    1 - price_at_decision
                                                )
                                                signed_market_series = 1 - market_series
                                            else:
                                                signed_price_at_decision = (
                                                    price_at_decision
                                                )
                                                signed_market_series = market_series

                                            # Get price at horizon
                                            future_prices = signed_market_series.loc[
                                                signed_market_series.index
                                                >= target_date
                                            ]
                                            if future_prices.empty:
                                                price_at_horizon = (
                                                    signed_market_series.dropna().iloc[
                                                        -1
                                                    ]
                                                )
                                            else:
                                                price_at_horizon = (
                                                    future_prices.dropna().iloc[0]
                                                    if not future_prices.dropna().empty
                                                    else signed_market_series.dropna().iloc[
                                                        -1
                                                    ]
                                                )

                                            if not pd.isna(price_at_horizon):
                                                market_return = (
                                                    price_at_horizon
                                                    / signed_price_at_decision
                                                    - 1
                                                ) * abs(market_decision.decision.bet)
                                                event_return += market_return

                    decision_return += event_return

        returns_by_model[model_id].append(decision_return)

    # Compute average returns across all decisions for each model
    avg_returns_by_model = {}
    for model_id, returns in returns_by_model.items():
        if returns:
            avg_returns_by_model[model_id] = np.mean(returns)
        else:
            avg_returns_by_model[model_id] = 0.0

    return avg_returns_by_model


def analyze_holding_horizons():
    """Main analysis function."""
    logger.info("Starting holding horizon analysis...")

    # Load data
    logger.info("Loading data...")
    model_decisions = load_investment_choices_from_google()
    events = get_non_duplicated_events(load_saved_events())
    market_prices = load_market_prices(events)
    prices_df = get_market_prices_dataframe(market_prices)
    prices_df = prices_df.sort_index()
    prices_df = _to_date_index(prices_df)

    logger.info(
        f"Loaded {len(model_decisions)} model decisions and {len(prices_df.columns)} markets"
    )

    # Define horizons to test
    horizons = [1, 2, 3, 5, 7, 10, 14, 21, 30]

    # Use the backend system with custom horizons to get exact results
    logger.info("Computing returns using backend system with custom horizons...")

    from predibench.backend.data_loader import get_data_for_backend

    # Use the backend directly to get performance data with custom horizons
    backend_data = get_data_for_backend(custom_horizons=horizons)

    # Extract returns directly from backend performance data using custom_horizon_returns
    results_by_horizon = {}

    for horizon in horizons:
        logger.info(f"Extracting {horizon}-day horizon returns...")
        avg_returns_by_model = {}

        for model_id, performance in backend_data.performance_per_model.items():
            # Use custom_horizon_returns for ALL horizons (including 1, 2, 7)
            if (
                performance.average_returns.custom_horizon_returns
                and horizon in performance.average_returns.custom_horizon_returns
            ):
                avg_returns_by_model[model_id] = (
                    performance.average_returns.custom_horizon_returns[horizon]
                )
            else:
                avg_returns_by_model[model_id] = 0.0

        results_by_horizon[horizon] = avg_returns_by_model

    # Convert to DataFrame for easier analysis
    results_df = pd.DataFrame(results_by_horizon).fillna(0)

    logger.info("Creating visualizations...")

    # Create output directory under frontend public
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "predibench-frontend-react/public/holding_horizon_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    avg_returns_by_horizon = results_df.mean(axis=0)
    best_horizons = results_df.idxmax(axis=1)
    horizon_counts = best_horizons.value_counts().sort_index()

    # Figure 1: Average Returns by Holding Horizon
    fig1 = go.Figure()

    # Main average line
    fig1.add_trace(
        go.Scatter(
            x=horizons,
            y=avg_returns_by_horizon.values,
            mode="lines+markers",
            name="Average Returns",
            line=dict(width=4, color="blue"),
            marker=dict(size=10),
        )
    )

    # Add individual model lines (top 10 models by performance)
    top_models = results_df.mean(axis=1).nlargest(10).index
    colors = [
        "rgba(255,0,0,0.4)",
        "rgba(0,255,0,0.4)",
        "rgba(255,165,0,0.4)",
        "rgba(255,255,0,0.4)",
        "rgba(255,0,255,0.4)",
        "rgba(0,255,255,0.4)",
        "rgba(128,0,128,0.4)",
        "rgba(0,128,0,0.4)",
        "rgba(128,128,128,0.4)",
        "rgba(255,192,203,0.4)",
    ]

    for i, model in enumerate(top_models):
        fig1.add_trace(
            go.Scatter(
                x=horizons,
                y=results_df.loc[model].values,
                mode="lines",
                name=f"{model[:25]}..." if len(model) > 25 else model,
                line=dict(color=colors[i % len(colors)], width=2),
                opacity=0.7,
            )
        )

    fig1.update_layout(
        xaxis_title="Holding Horizon (Days)",
        yaxis_title="Average Return",
        height=600,
        width=1000,
        showlegend=True,
    )

    apply_template(fig1)
    fig1.write_json(output_dir / "1_average_returns_by_horizon.json")
    logger.info(f"Saved Figure 1 to {output_dir / '1_average_returns_by_horizon.json'}")

    # Figure 2: Best Horizon Distribution
    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=horizon_counts.index,
            y=horizon_counts.values,
            name="Best Horizon Count",
            marker_color="lightcoral",
            text=horizon_counts.values,
            textposition="auto",
        )
    )

    fig2.update_layout(
        xaxis_title="Holding Horizon (Days)",
        yaxis_title="Number of Models",
        height=600,
        width=800,
    )

    apply_template(fig2)
    fig2.write_json(output_dir / "2_optimal_horizon_distribution.json")
    logger.info(
        f"Saved Figure 2 to {output_dir / '2_optimal_horizon_distribution.json'}"
    )

    # Figure 3: Return Distribution by Horizon (Box plots)
    fig3 = go.Figure()

    for horizon in horizons:
        fig3.add_trace(
            go.Box(
                y=results_df[horizon].values,
                name=f"{horizon} days",
                boxpoints="outliers",
            )
        )

    fig3.update_layout(
        xaxis_title="Holding Horizon",
        yaxis_title="Return Distribution",
        height=600,
        width=1000,
    )

    apply_template(fig3)
    fig3.write_json(output_dir / "3_return_distribution_by_horizon.json")
    logger.info(
        f"Saved Figure 3 to {output_dir / '3_return_distribution_by_horizon.json'}"
    )

    # Figure 4: Heatmap of top models' performance across horizons
    top_20_models = results_df.mean(axis=1).nlargest(20).index
    heatmap_data = results_df.loc[top_20_models]

    fig4 = go.Figure()
    fig4.add_trace(
        go.Heatmap(
            z=heatmap_data.values,
            x=[f"{h}d" for h in horizons],
            y=[
                model[:35] + "..." if len(model) > 35 else model
                for model in top_20_models
            ],
            colorscale="RdYlGn",
            colorbar=dict(title="Average Return"),
        )
    )

    fig4.update_layout(
        xaxis_title="Holding Horizon",
        yaxis_title="Models",
        height=1600,
        width=1200,
    )

    apply_template(fig4)
    fig4.write_json(output_dir / "4_model_performance_heatmap.json")
    logger.info(f"Saved Figure 4 to {output_dir / '4_model_performance_heatmap.json'}")

    # Print summary statistics
    logger.info("\n=== HOLDING HORIZON ANALYSIS SUMMARY ===")
    logger.info(
        f"Optimal horizon (highest average return): {avg_returns_by_horizon.idxmax()} days"
    )
    logger.info(f"Best average return: {avg_returns_by_horizon.max():.4f}")
    logger.info(f"Worst average return: {avg_returns_by_horizon.min():.4f}")

    logger.info("\nAverage returns by horizon:")
    for horizon in horizons:
        logger.info(f"  {horizon:2d} days: {avg_returns_by_horizon[horizon]:7.4f}")

    logger.info(
        f"\nMost common best horizon across models: {best_horizons.mode().iloc[0]} days"
    )
    logger.info(
        f"Models with best performance at this horizon: {horizon_counts[best_horizons.mode().iloc[0]]}"
    )

    # Save raw results
    results_df.to_csv(output_dir / "holding_horizon_results.csv")
    logger.info(f"Saved raw results to {output_dir / 'holding_horizon_results.csv'}")

    return results_df, avg_returns_by_horizon


if __name__ == "__main__":
    results_df, avg_returns = analyze_holding_horizons()
