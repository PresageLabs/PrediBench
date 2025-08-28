from datetime import date, datetime, time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from predibench.brier import BrierScoreCalculator
from predibench.logger_config import get_logger
from predibench.polymarket_api import Market, MarketsRequestParameters

logger = get_logger(__name__)


class PnlCalculator:
    sharpe_constant_normalization = 252**0.5

    def __init__(
        self,
        positions: pd.DataFrame,
        prices: pd.DataFrame,
        to_vol_target: bool = False,
        vol_targeting_window: str = "30D",
    ):
        """
        positions: Daily positions: pd.DataFrame with columns as markets and index as dates. A position noted with date D as index is the position at the end of day D, which will be impacted by returns of day D+1
        returns: Daily returns: pd.DataFrame with columns as markets and index as dates. These can be absolute or relative, but if they're relative the sum across portfolio won't mean anything.
        prices: Price data: pd.DataFrame with columns as markets and index as dates
        to_vol_target: bool, if True, will target volatility
        vol_targeting_window: str, window for volatility targeting
        """
        self.positions = positions
        self.returns = prices.pct_change(periods=1).copy()
        self._assert_index_is_date(self.positions)
        self._assert_index_is_date(self.returns)
        self.prices = prices
        self._assert_index_is_date(self.prices)
        self.to_vol_target = to_vol_target
        self.vol_targeting_window = vol_targeting_window
        self.pnl = self.calculate_pnl()
        self.portfolio_daily_pnl = self.pnl.sum(
            axis="columns"
        )  # NOTE: this assumes all positions equal, it's false ofc
        self.portfolio_cumulative_pnl = self.portfolio_daily_pnl.cumsum()
        self.portfolio_mean_pnl = self.portfolio_daily_pnl.mean()
        self.portfolio_std_pnl = self.portfolio_daily_pnl.std()
        self.portfolio_sum_pnl = self.portfolio_daily_pnl.sum()

    def _assert_index_is_date(self, df: pd.DataFrame):
        assert all(isinstance(idx, date) for idx in df.index), (
            "All index values must be date objects or timestamps without time component"
        )

    def _get_positions_begin_next_day(self, col: str):
        """
        Align positions with returns by shifting position dates forward by 1 day.
        Position held at end of day D should capture returns on day D+1.
        """
        positions_series = self.positions[col].copy()
        # Shift index forward by 1 day to align with when returns are realized
        positions_series.index = positions_series.index + pd.Timedelta(days=1)
        return positions_series

    def calculate_pnl(self):
        if self.to_vol_target:
            volatility = (
                self.returns.apply(
                    lambda x: x.dropna().rolling(self.vol_targeting_window).std()
                )
                .resample("1D")
                .last()
                .ffill()
            )
            self.new_positions = (
                (self.positions / volatility).resample("1D").last().ffill(limit=7)
            )
            pnls = pd.concat(
                [
                    self.new_positions[col]
                    .reindex(self.returns[col].dropna().index)
                    .shift(1)
                    * self.returns[col]
                    for col in self.new_positions
                ],
                axis="columns",
            )
            return pnls
        else:
            logger.debug("Profit calculation debug info")
            logger.debug(f"Returns head:\n{self.returns.head()}")
            logger.debug(f"Positions head:\n{self.positions.head()}")
            pnls = pd.concat(
                [
                    self._get_positions_begin_next_day(col).reindex(
                        self.returns[col].dropna().index, fill_value=0
                    )
                    * self.returns[col]
                    for col in self.positions
                ],
                axis="columns",
            )
            return pnls

    def plot_pnl(self, stock_details: bool = False):
        if not stock_details:
            fig = px.line(
                x=self.portfolio_cumulative_pnl.index,
                y=self.portfolio_cumulative_pnl,
                labels={"x": "Date", "y": "Cumulative Profit"},
            )
            fig.data[0].update(mode="markers+lines")
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative Profit",
            )
            return fig
        else:
            # Create subplots: Prices on top, Profit on bottom (equal height)
            fig = make_subplots(
                rows=2,
                cols=1,
                row_heights=[0.5, 0.5],  # Equal height for both subplots
                subplot_titles=("Price Evolution", "Cumulative Profit"),
                vertical_spacing=0.08,
            )

            colors = px.colors.qualitative.Plotly
            columns = list(self.pnl.columns)
            for i, market_id in enumerate(columns):
                col_color = colors[i % len(colors)]
                cumulative_pnl_market = self.pnl[market_id].cumsum(axis="index")

                # Add price evolution trace to subplot 1 (top)
                if market_id in self.prices.columns:
                    price_data = self.prices[market_id].dropna()
                    fig.add_trace(
                        go.Scatter(
                            x=price_data.index,
                            y=price_data.values,
                            mode="lines",
                            name=market_id[:40],
                            line=dict(color=col_color),
                            legendgroup=market_id[:40],
                        ),
                        row=1,
                        col=1,
                    )

                    # Add markers for positions taken on the price chart
                    positions_to_plot = self.positions[market_id][
                        self.positions[market_id].notna()
                    ]

                    if len(positions_to_plot) > 0:
                        # Get price values at position change dates
                        inter_index = positions_to_plot.index.intersection(
                            price_data.index
                        )
                        prices_at_positions = price_data.loc[inter_index]
                        positions_to_plot = positions_to_plot.loc[inter_index]
                        fig.add_trace(
                            go.Scatter(
                                x=prices_at_positions.index,
                                y=prices_at_positions.values,
                                text=positions_to_plot.values,
                                hovertemplate="Date: %{x}<br>Position: %{text:.2f}<br>Price: %{y:.3f}<extra></extra>",
                                mode="markers",
                                marker=dict(
                                    symbol=[
                                        "triangle-up"
                                        if pos > 0
                                        else "triangle-down"
                                        if pos < 0
                                        else "circle"
                                        for pos in positions_to_plot.values
                                    ],
                                    size=10,
                                    color=col_color,
                                    line=dict(width=1, color="black"),
                                ),
                                showlegend=False,
                                legendgroup=market_id[:40],
                                name="Positions - " + market_id[:40],
                            ),
                            row=1,
                            col=1,
                        )

                # Add Profit trace to subplot 2 (bottom)
                fig.add_trace(
                    go.Scatter(
                        x=cumulative_pnl_market.index,
                        y=cumulative_pnl_market.values,
                        mode="markers+lines",
                        line=dict(color=col_color),
                        showlegend=False,
                        legendgroup=market_id[:40],
                        name=market_id[:40],
                    ),
                    row=2,
                    col=1,
                )

            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(
                title_text="Cumulative Profit", tickformat=".1f", row=2, col=1
            )
            fig.update_layout(
                legend_title="Stock",
                width=1200,
                height=800,  # Increased height for two subplots
            )
            return fig

    def vol_pnl_daily(self):
        return self.portfolio_std_pnl

    def vol_pnl_annualized(self):
        return self.portfolio_std_pnl * self.sharpe_constant_normalization

    def sharpe_daily(self):
        return self.portfolio_mean_pnl / self.portfolio_std_pnl

    def sharpe_annualized(self):
        return (
            self.portfolio_mean_pnl
            / self.portfolio_std_pnl
            * self.sharpe_constant_normalization
        )

    def compute_sortino_ratio(self, risk_free_rate: float = 0.0):
        """
        Sortino Ratio = (Mean Return - Risk-Free Rate) / Downside Deviation
        """
        excess_returns = self.portfolio_daily_pnl - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = np.std(downside_returns, ddof=1)
        if downside_deviation == 0:
            return np.inf
        return excess_returns.mean() / downside_deviation

    def max_drawdown(self):
        """
        Maximum Drawdown = (Peak - Trough) / Peak
        Assumes daily returns
        """
        cumulative_returns = self.portfolio_cumulative_pnl
        peak = cumulative_returns.cummax()
        drawdown = (peak - cumulative_returns) / peak
        return drawdown.max()

    def compute_calmar_ratio(self, risk_free_rate: float = 0.0):
        """
        Calmar Ratio = Annualized Return / Maximum Drawdown
        Assumes daily returns
        """
        max_drawdown = self.max_drawdown()
        annualized_return = self.portfolio_mean_pnl * 252
        if max_drawdown == 0:
            return np.inf
        return annualized_return / abs(max_drawdown)

    def turnover(self):
        """
        Calculate turnover in %.
        """
        turnover = (
            100
            * self.positions.diff().abs().sum(axis=1).sum()
            / self.positions.abs().sum(axis=1).sum()
        )
        return turnover

    def get_performance_metrics(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(
            {
                "Sharpe Ratio (Daily)": [self.sharpe_daily()],
                "Sharpe Ratio (Annualized)": [self.sharpe_annualized()],
                "Volatility (Daily)": [self.vol_pnl_daily()],
                "Volatility (Annualized)": [self.vol_pnl_annualized()],
                "Sortino Ratio": [self.compute_sortino_ratio()],
                "Maximum Drawdown": [self.max_drawdown()],
                "Calmar Ratio": [self.compute_calmar_ratio()],
                "Turnover (%)": [self.turnover()],
            },
            columns=["Value"],
            orient="index",
        )


def validate_continuous_prices(prices_df: pd.DataFrame) -> None:
    """Validate that this dataframe's date index is continuous"""
    start_date = prices_df.index.min()
    end_date = prices_df.index.max()
    expected_date_range = pd.date_range(start=start_date, end=end_date, freq="D").date
    actual_dates = set(prices_df.index)
    expected_dates = set(expected_date_range)

    missing_dates = expected_dates - actual_dates
    if missing_dates:
        raise ValueError(f"Missing returns data for dates: {sorted(missing_dates)}")


def get_pnls(
    positions_df: pd.DataFrame,
    end_date: date | None = None,
    write_plots: bool = False,
) -> dict[str, PnlCalculator]:
    """Builds Profit calculators for each agent in the positions dataframe.

    Args:
        positions_df: DataFrame with positions data, with columns [agent_name, market_id, date]
        write_plots: bool, if True, will write plots to the current directory
        end_date: cutoff date
    """
    # Validate that we have continuous returns data
    markets = {}
    for market_id in positions_df["market_id"].unique():
        request_parameters = MarketsRequestParameters(
            id=market_id,
        )
        market = request_parameters.get_markets(
            end_datetime=datetime.combine(end_date, time(0, 0, 0))
            if end_date
            else None,
            # 15 days back is the maximum allowed by the API
        )[0]
        markets[market_id] = market
    prices_df = get_historical_returns(markets)

    validate_continuous_prices(prices_df)

    pnl_calculators = {}
    for agent_name in positions_df["agent_name"].unique():
        print("AGENT NAME", agent_name)
        positions_agent_df = positions_df[
            positions_df["agent_name"] == agent_name
        ].drop(columns=["agent_name"])
        positions_agent_df = positions_agent_df.loc[
            positions_agent_df["date"].isin(positions_df["date"].unique())
        ]
        positions_agent_df = positions_agent_df.loc[
            positions_df["market_id"].isin(prices_df.columns)
        ]  # TODO: This should be removed when we can save
        assert len(positions_agent_df) > 0, (
            "A this stage, dataframe should not be empty!"
        )

        pnl_calculator = get_pnl_calculator(
            positions_agent_df,
            prices_df,
            positions_df["date"].unique(),
        )
        pnl_calculators[agent_name] = pnl_calculator

    return pnl_calculators


def get_pnl_calculator(
    positions_agent_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    investment_dates: list,
) -> PnlCalculator:
    # Convert positions_agent_df to have date as index, question as columns, and choice as values
    positions_agent_df = positions_agent_df.pivot(
        index="date", columns="market_id", values="choice"
    )

    # Forward-fill positions to all daily dates in the returns range
    daily_index = prices_df.index[prices_df.index >= investment_dates[0]]
    positions_agent_df = positions_agent_df.reindex(daily_index, method="ffill").fillna(
        0
    )  # fillna(0) to avoid NaN at the beginning of the investment period
    positions_agent_df = positions_agent_df.loc[
        positions_agent_df.index >= investment_dates[0]
    ]
    prices_df = prices_df.loc[prices_df.index >= investment_dates[0]]

    logger.info("Analyzing portfolio performance with PnlCalculator...")

    logger.info("Positions Table (first 15 rows):")
    logger.info(f"\n{positions_agent_df.head(15)}")
    logger.info(f"Positions shape: {positions_agent_df.shape}")

    logger.info("Returns Table (first 15 rows):")

    logger.info("Data summary:")
    logger.info(
        f"  Investment positions: {(positions_agent_df != 0.0).sum().sum()} out of {positions_agent_df.size} possible"
    )

    return PnlCalculator(positions_agent_df, prices_df)


def get_historical_returns(
    markets: dict[str, Market],
) -> pd.DataFrame:
    """Get historical prices directly from timeseries data. Columns are market ids"""
    prices_df = pd.DataFrame(
        np.nan,
        index=markets[list(markets.keys())[0]].prices.index,
        columns=list(markets.keys()),
    )

    for market in markets.values():
        prices_df[market.id] = market.prices
    return prices_df
