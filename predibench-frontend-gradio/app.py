from datetime import date, datetime

import gradio as gr
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datasets import load_dataset
from predibench.backend.pnl import get_pnls

# Set Plotly dark theme as default
pio.templates.default = "plotly_dark"

# Configuration
AGENT_CHOICES_REPO = "m-ric/predibench-agent-choices"


def load_agent_choices():
    """Load agent choices from HuggingFace dataset"""
    dataset = load_dataset(AGENT_CHOICES_REPO, split="train")
    dataset = dataset.to_pandas()
    return dataset.sort_values("date")


def add_rationale_markers(
    fig: go.Figure, agent_data: pd.DataFrame, prices: pd.DataFrame
):
    """Add square markers with rationale to the price chart for each position taken"""
    colors = px.colors.qualitative.Plotly

    for i, (market_id, market_positions) in enumerate(agent_data.groupby("market_id")):
        col_color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(
                x=market_positions["date"],
                y=prices.loc[market_positions["date"]][market_id],
                mode="markers",
                marker=dict(
                    symbol="square",
                    size=12,
                    color=col_color,
                    line=dict(width=2, color="black"),
                ),
                hovertemplate="<b>Position Taken</b><br>"
                + "Date: %{x}<br>"
                + "Market: "
                + str(market_id)[:40]
                + "<br>"
                + "Choice: %{customdata[0]}<br>"
                + "Rationale: %{customdata[1]}<br>"
                + "<extra></extra>",
                customdata=list(
                    zip(market_positions["choice"], market_positions["rationale"])
                ),
                showlegend=False,
                name=f"Positions - {str(market_id)[:20]}",
            ),
            row=1,  # Add to the price chart (top subplot)
            col=1,
        )

    return fig


def calculate_pnl_and_performance(positions_df: pd.DataFrame):
    """Calculate real Profit and performance metrics for each agent using historical market data"""
    positions_df = positions_df.loc[positions_df["date"] > date(2025, 7, 19)]
    pnl_results = get_pnls(positions_df)

    # We need to load prices separately for plotting
    from predibench.backend.pnl import get_historical_returns
    from predibench.backend.data_loader import load_market_prices
    market_prices = load_market_prices()
    prices_df = get_historical_returns(market_prices)

    # Convert to the format expected by frontend
    agents_performance = {}
    for agent in positions_df["model_name"].unique():
        pnl_result = pnl_results[agent]
        agent_data = positions_df[positions_df["model_name"] == agent].copy()
        daily_pnl = pnl_result["portfolio_daily_pnl"]

        # Create a simple plot instead of using the class method
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           subplot_titles=['Cumulative PnL', 'Prices'])
        
        # Add cumulative PnL trace
        fig.add_trace(
            go.Scatter(x=pnl_result["portfolio_cumulative_pnl"].index, 
                      y=pnl_result["portfolio_cumulative_pnl"].values,
                      name="Cumulative PnL"),
            row=1, col=1
        )
        
        # Add price traces for each market
        for col in prices_df.columns:
            if col in pnl_result["pnl"].columns:
                fig.add_trace(
                    go.Scatter(x=prices_df.index, y=prices_df[col].values,
                              name=f"Price {col[:20]}..."),
                    row=2, col=1
                )

        # Enhance the figure with rationale markers
        enhanced_figure = add_rationale_markers(fig, agent_data, prices_df)

        agents_performance[agent] = {
            "long_positions": len(agent_data[agent_data["choice"] == 1]),
            "short_positions": len(agent_data[agent_data["choice"] == -1]),
            "no_positions": len(agent_data[agent_data["choice"] == 0]),
            "final_cumulative_pnl": pnl_result["portfolio_cumulative_pnl"].iloc[-1],
            "annualized_sharpe_ratio": (daily_pnl.mean() / daily_pnl.std())
            * np.sqrt(252),
            "daily_cumulative_pnl": pnl_result["portfolio_cumulative_pnl"].tolist(),
            "dates": pnl_result["portfolio_cumulative_pnl"].index.tolist(),
            "figure": enhanced_figure,
        }

    return agents_performance


def create_leaderboard(performance_data):
    """Create leaderboard table"""
    leaderboard_data = []

    for agent, metrics in performance_data.items():
        leaderboard_data.append(
            {
                "Agent": agent.replace("smolagent_", "").replace("--", "/"),
                "Final cumulative Profit": f"{metrics['final_cumulative_pnl']:.3f}",
                "Annualized Sharpe Ratio": f"{metrics['annualized_sharpe_ratio']:.3f}",
                "Long Positions": metrics["long_positions"],
                "Short Positions": metrics["short_positions"],
                "No Position": metrics["no_positions"],
            }
        )

    # Sort by cumulative Profit
    leaderboard_df = pd.DataFrame(leaderboard_data)
    leaderboard_df["PnL_numeric"] = leaderboard_df["Final cumulative Profit"].astype(
        float
    )
    leaderboard_df = leaderboard_df.sort_values("PnL_numeric", ascending=False)
    leaderboard_df = leaderboard_df.drop("PnL_numeric", axis=1)

    return leaderboard_df


def create_pnl_plot(performance_data):
    """Create interactive Profit plot"""
    fig = go.Figure()

    colors = px.colors.qualitative.Set1

    # Sort agents by descending final Profit
    sorted_agents = sorted(
        performance_data.keys(),
        key=lambda agent: performance_data[agent]["final_cumulative_pnl"],
        reverse=True,
    )

    for i, agent in enumerate(sorted_agents):
        if agent not in performance_data:
            continue

        metrics = performance_data[agent]
        daily_cumulative_pnl = metrics["daily_cumulative_pnl"]
        dates = metrics["dates"]

        # Calculate cumulative Profit over time
        plot_dates = [dates[0]] + dates if dates else [datetime.now()]

        fig.add_trace(
            go.Scatter(
                x=plot_dates,
                y=daily_cumulative_pnl,
                name=agent.replace("smolagent_", "").replace("--", "/"),
                line=dict(color=colors[i % len(colors)], width=2),
                mode="lines+markers",
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Date: %{x}<br>"
                + "Cumulative Profit: %{y:.2f}<br>"
                + "<extra></extra>",
            )
        )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Profit",
        hovermode="x unified",
        height=500,
        showlegend=True,
        yaxis=dict(tickformat=".2f"),
    )

    # Add horizontal line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    return fig


df = load_agent_choices()

df["timestamp_uploaded"] = pd.to_datetime(df["timestamp_uploaded"])
cutoff_date = pd.to_datetime("2025-08-18")
df = df[df["timestamp_uploaded"] < cutoff_date]
performance_data = calculate_pnl_and_performance(df)

with gr.Blocks(title="PrediBench Leaderboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏆 PrediBench - Can LLMs predict the future?")
    gr.Markdown(
        f"Track the performance of AI agents making predictions on Polymarket questions. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    with gr.Tabs():
        with gr.TabItem("🏆 Leaderboard"):
            leaderboard_table = gr.Dataframe(
                value=create_leaderboard(performance_data), interactive=False, wrap=True
            )

            pnl_plot = gr.Plot(
                value=create_pnl_plot(performance_data),
                label="Cumulative Profit Over Time",
            )

        with gr.TabItem("🔍 Portfolio Details"):
            with gr.Row():
                portfolio_dropdown = gr.Dropdown(
                    choices=[agent for agent in performance_data.keys()],
                    value=list(performance_data.keys())[0]
                    if performance_data
                    else None,
                    label="Select model",
                    scale=3,
                )

            portfolio_plot = gr.Plot(
                value=performance_data[list(performance_data.keys())[0]]["figure"]
                if performance_data
                else None,
                label="Cumulative Profit Over Time",
            )

            # Update portfolio plot when agent selection changes
            def update_portfolio_plot(selected_agent):
                if selected_agent and selected_agent in performance_data:
                    return performance_data[selected_agent]["figure"]
                return None

            portfolio_dropdown.change(
                fn=update_portfolio_plot,
                inputs=portfolio_dropdown,
                outputs=portfolio_plot,
            )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)
