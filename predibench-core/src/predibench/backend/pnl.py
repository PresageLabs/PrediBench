from datetime import date, datetime, time
from functools import lru_cache
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from predibench.backend.data_loader import load_agent_position, load_market_prices
from predibench.logger_config import get_logger
from predibench.polymarket_api import Market, MarketsRequestParameters

logger = get_logger(__name__)


def _assert_index_is_date(df: pd.DataFrame):
    assert all(isinstance(idx, date) for idx in df.index), (
        "All index values must be date objects or timestamps without time component"
    )


def _get_positions_begin_next_day(positions: pd.DataFrame, col: str):
    """
    Align positions with returns by shifting position dates forward by 1 day.
    Position held at end of day D should capture returns on day D+1.
    """
    positions_series = positions[col].copy()
    # Shift index forward by 1 day to align with when returns are realized
    positions_series.index = positions_series.index + pd.Timedelta(days=1)
    return positions_series


def calculate_pnl(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    to_vol_target: bool = False,
    vol_targeting_window: str = "30D",
):
    """
    Calculate profit and loss for given positions and prices.
    
    Args:
        positions: Daily positions: pd.DataFrame with columns as markets and index as dates. 
                  A position noted with date D as index is the position at the end of day D, 
                  which will be impacted by returns of day D+1
        prices: Price data: pd.DataFrame with columns as markets and index as dates
        to_vol_target: bool, if True, will target volatility
        vol_targeting_window: str, window for volatility targeting
        
    Returns:
        dict containing:
            - pnl: DataFrame with PnL values
            - portfolio_daily_pnl: Series with daily portfolio PnL
            - portfolio_cumulative_pnl: Series with cumulative portfolio PnL  
            - portfolio_mean_pnl: float with mean daily PnL
            - portfolio_std_pnl: float with std of daily PnL
            - portfolio_sum_pnl: float with total PnL
    """
    returns = prices.pct_change(periods=1, fill_method=None).copy()
    _assert_index_is_date(positions)
    _assert_index_is_date(returns)
    _assert_index_is_date(prices)
    
    if to_vol_target:
        volatility = (
            returns.apply(
                lambda x: x.dropna().rolling(vol_targeting_window).std()
            )
            .resample("1D")
            .last()
            .ffill()
        )
        new_positions = (
            (positions / volatility).resample("1D").last().ffill(limit=7)
        )
        pnl = pd.concat(
            [
                new_positions[col]
                .reindex(returns[col].dropna().index)
                .shift(1)
                * returns[col]
                for col in new_positions
            ],
            axis="columns",
        )
    else:
        logger.debug("Profit calculation debug info")
        logger.debug(f"Returns head:\n{returns.head()}")
        logger.debug(f"Positions head:\n{positions.head()}")
        pnl = pd.concat(
            [
                _get_positions_begin_next_day(positions, col).reindex(
                    returns[col].dropna().index, fill_value=0
                )
                * returns[col]
                for col in positions
            ],
            axis="columns",
        )
    
    portfolio_daily_pnl = pnl.sum(axis="columns")
    portfolio_cumulative_pnl = portfolio_daily_pnl.cumsum()
    portfolio_mean_pnl = portfolio_daily_pnl.mean()
    portfolio_std_pnl = portfolio_daily_pnl.std()
    portfolio_sum_pnl = portfolio_daily_pnl.sum()
    
    return {
        "pnl": pnl,
        "portfolio_daily_pnl": portfolio_daily_pnl,
        "portfolio_cumulative_pnl": portfolio_cumulative_pnl,
        "portfolio_mean_pnl": portfolio_mean_pnl,
        "portfolio_std_pnl": portfolio_std_pnl,
        "portfolio_sum_pnl": portfolio_sum_pnl,
    }







def get_pnls(
    positions_df: pd.DataFrame,
) -> dict[str, dict]:
    """Builds PnL calculations for each agent in the positions dataframe.

    Args:
        positions_df: DataFrame with positions data, with columns [model_name, market_id, date]
        write_plots: bool, if True, will write plots to the current directory
        end_date: cutoff date
    """
    
    market_prices = load_market_prices()
    prices_df = get_historical_returns(market_prices)

    pnl_results = {}
    for model_name in positions_df["model_name"].unique():
        print("AGENT NAME", model_name)
        positions_agent_df = positions_df[
            positions_df["model_name"] == model_name
        ].drop(columns=["model_name"])
        assert len(positions_agent_df) > 0, (
            "A this stage, dataframe should not be empty!"
        )
        positions_agent_df = positions_agent_df.pivot(
        index="date", columns="market_id", values="choice"
    )

        pnl_result = calculate_pnl(
            positions_agent_df,
            prices_df,
        )
        pnl_results[model_name] = pnl_result

    return pnl_results


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
    if len(unified_index) > 0 and hasattr(unified_index[0], 'tz') and unified_index[0].tz is not None:
        unified_index = unified_index.tz_convert('UTC').date
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
        if len(prices) > 0 and hasattr(prices.index[0], 'tz') and prices.index[0].tz is not None:
            # Convert timezone-aware prices index to timezone-naive dates
            prices_dates = prices.index.tz_convert('UTC').date
            prices_date_index = pd.DatetimeIndex([pd.Timestamp(d) for d in prices_dates])
            prices_aligned = pd.Series(prices.values, index=prices_date_index)
            # Remove duplicates by keeping the last value for each date
            prices_aligned = prices_aligned[~prices_aligned.index.duplicated(keep='last')]
            prices_df[market_id] = prices_aligned
        else:
            prices_df[market_id] = prices
    
    return prices_df



@lru_cache(maxsize=1)
def get_positions_df():
    # Calculate market-level data
    data = load_agent_position()

    # Working with Pydantic models from GCP
    positions = []
    for model_result in data:
        model_name = model_result.model_info.model_pretty_name
        date = model_result.target_date

        for event_decision in model_result.event_investment_decisions:
            for market_decision in event_decision.market_investment_decisions:
                positions.append(
                    {
                        "date": date,
                        "market_id": market_decision.market_id,
                        "choice": market_decision.model_decision.bet,
                        "model_name": model_name,
                    }
                )

    return pd.DataFrame.from_records(positions)


@lru_cache(maxsize=1)
def get_all_markets_pnls():
    positions_df = get_positions_df()
    pnl_results = get_pnls(positions_df)
    return pnl_results
