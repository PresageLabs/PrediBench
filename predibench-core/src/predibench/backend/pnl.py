from datetime import date

import numpy as np
import pandas as pd
from predibench.logger_config import get_logger

logger = get_logger(__name__)


def _assert_index_is_date(df: pd.DataFrame):
    assert all(isinstance(idx, date) for idx in df.index), (
        "All index values must be date objects or timestamps without time component"
    )


def compute_pnl_series_per_model(
    positions_agent_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> tuple[pd.Series, dict[str, pd.Series]]:
    """
    Compute portfolio and per-market cumulative PnL series for a single model.

    Returns a tuple:
      - portfolio_cumulative_pnl: pd.Series indexed by date with cumulative PnL
      - market_cumulative_pnls: dict mapping market_id -> pd.Series cumulative PnL
    """
    _assert_index_is_date(positions_agent_df)
    _assert_index_is_date(prices_df)

    market_pnl_series: dict[str, pd.Series] = {}

    for market_id in positions_agent_df.columns:
        if market_id not in prices_df.columns:
            logger.warning(f"Market {market_id} not found in prices data, skipping")
            continue

        agent_positions_series = positions_agent_df[market_id]
        market_prices_raw = prices_df[market_id]
        market_prices = market_prices_raw.interpolate(method="linear").dropna()

        valid_positions = agent_positions_series.dropna()
        if len(valid_positions) == 0 or len(market_prices) == 0:
            continue

        first_bet_date = valid_positions.index.min()
        last_market_date = market_prices.index.max()
        if first_bet_date > last_market_date:
            logger.warning(
                f"Agent started betting after market {market_id} ended; skipping"
            )
            continue

        market_date_range = pd.date_range(
            start=first_bet_date, end=last_market_date, freq="D"
        )
        market_date_range = pd.Index([d.date() for d in market_date_range])
        market_date_range = market_date_range.intersection(market_prices.index)
        if len(market_date_range) == 0:
            continue

        extended_positions = (
            agent_positions_series.reindex(market_date_range).ffill().fillna(0)
        )
        aligned_prices = market_prices.reindex(market_date_range, method="ffill")
        price_changes = aligned_prices.diff().fillna(0)
        daily_pnl = extended_positions.shift(1, fill_value=0) * price_changes
        market_pnl_series[market_id] = daily_pnl

    if not market_pnl_series:
        # Return empty aligned series
        return pd.Series(dtype=float), {}

    all_dates = set()
    for pnl_series in market_pnl_series.values():
        all_dates.update(pnl_series.index)
    all_dates = sorted(all_dates)

    portfolio_daily_pnl = pd.Series(0.0, index=all_dates)
    for market_daily in market_pnl_series.values():
        aligned = market_daily.reindex(all_dates, fill_value=0.0)
        portfolio_daily_pnl += aligned

    portfolio_cumulative_pnl = portfolio_daily_pnl.cumsum()

    market_cumulative_pnls: dict[str, pd.Series] = {}
    for market_id, daily in market_pnl_series.items():
        market_cumulative_pnls[market_id] = daily.cumsum()

    return portfolio_cumulative_pnl, market_cumulative_pnls


def get_historical_returns(
    market_prices: dict[str, pd.Series],
) -> pd.DataFrame:
    """Get historical prices directly from timeseries data. Columns are market ids

    Creates a unified DataFrame with all markets, handling cases where markets
    have different start/end dates by using a unified date index.

    Args:
        market_prices: Dictionary mapping market_id to price Series

    Returns:
        DataFrame with unified date index and market_ids as columns
    """
    # Collect all unique dates from all markets to create unified index
    all_dates = set()
    valid_market_prices = {}

    for market_id, prices in market_prices.items():
        if prices is not None and len(prices) > 0:
            all_dates.update(prices.index)
            valid_market_prices[market_id] = prices

    if not all_dates:
        # Return empty DataFrame if no valid price data
        return pd.DataFrame(columns=list(market_prices.keys()))

    # Create unified date index, convert to timezone-naive dates to match positions data
    unified_index = pd.Index(sorted(all_dates))

    # Convert timezone-aware datetimes to timezone-naive dates for consistency with positions
    if (
        len(unified_index) > 0
        and hasattr(unified_index[0], "tz")
        and unified_index[0].tz is not None
    ):
        unified_index = unified_index.tz_convert("UTC").date
        unified_index = pd.DatetimeIndex([pd.Timestamp(d) for d in unified_index])
        # Remove duplicate dates
        unified_index = unified_index[~unified_index.duplicated()]

    # Initialize DataFrame with NaN values
    prices_df = pd.DataFrame(
        np.nan,
        index=unified_index,
        columns=list(market_prices.keys()),
    )

    # Fill in price data for each market
    for market_id, prices in valid_market_prices.items():
        if (
            len(prices) > 0
            and hasattr(prices.index[0], "tz")
            and prices.index[0].tz is not None
        ):
            # Convert timezone-aware prices index to timezone-naive dates
            prices_dates = prices.index.tz_convert("UTC").date
            prices_date_index = pd.DatetimeIndex(
                [pd.Timestamp(d) for d in prices_dates]
            )
            prices_aligned = pd.Series(prices.values, index=prices_date_index)
            # Remove duplicates by keeping the last value for each date
            prices_aligned = prices_aligned[
                ~prices_aligned.index.duplicated(keep="last")
            ]
            prices_df[market_id] = prices_aligned
        else:
            prices_df[market_id] = prices

    return prices_df
