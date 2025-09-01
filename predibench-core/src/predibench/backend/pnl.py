from datetime import date, datetime, time
from functools import lru_cache
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from predibench.backend.data_loader import load_agent_position
from predibench.logger_config import get_logger
from predibench.polymarket_api import Market, MarketsRequestParameters
from predibench.backend.data_model import PnlResult, DataPoint

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
    positions_agent_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> PnlResult:
    """
    Calculate profit and loss for given positions and prices.
    
    For prediction markets: PnL = position_size * (price_today - price_yesterday)
    
    Args:
        positions_agent_df: Daily positions DataFrame with dates as index, markets as columns
        prices_df: Price data DataFrame with dates as index, markets as columns
        
    Returns:
        PnlResult with cumulative PnL time series and final value
    """
    _assert_index_is_date(positions_agent_df)
    _assert_index_is_date(prices_df)
    
    # Calculate price changes (not percentage returns)
    price_changes = prices_df.diff().fillna(0)
    
    # Align positions and price changes to same date range
    aligned_dates = price_changes.index.intersection(positions_agent_df.index)
    if len(aligned_dates) == 0:
        # Return empty results if no overlapping dates
        return PnlResult(
            cumulative_pnl=[],
            final_pnl=0.0
        )
    
    # Calculate PnL for each market
    market_pnls = {}
    for market_id in positions_agent_df.columns:
        if market_id in price_changes.columns:
            # Get positions and price changes for this market
            positions = positions_agent_df[market_id].reindex(aligned_dates, fill_value=0)
            price_change = price_changes[market_id].reindex(aligned_dates, fill_value=0)
            
            # PnL = previous_day_position * price_change
            # Shift positions by 1 day since position held yesterday affects today's PnL
            market_pnl = positions.shift(1, fill_value=0) * price_change
            market_pnls[market_id] = market_pnl
    
    # Create PnL DataFrame
    if market_pnls:
        pnl_df = pd.DataFrame(market_pnls, index=aligned_dates)
    else:
        pnl_df = pd.DataFrame(index=aligned_dates)
    
    # Calculate portfolio-level metrics (only what we need)
    portfolio_daily_pnl = pnl_df.sum(axis=1) if len(pnl_df.columns) > 0 else pd.Series(0.0, index=aligned_dates)
    portfolio_cumulative_pnl = portfolio_daily_pnl.cumsum()
    
    # Convert to DataPoints for frontend
    cumulative_pnl_points = []
    for date_idx, pnl_value in portfolio_cumulative_pnl.items():
        cumulative_pnl_points.append(
            DataPoint(
                date=date_idx.strftime("%Y-%m-%d"),
                value=float(pnl_value)
            )
        )
    
    final_pnl = float(portfolio_cumulative_pnl.iloc[-1]) if len(portfolio_cumulative_pnl) > 0 else 0.0
    
    logger.debug(f"Calculated PnL for {len(market_pnls)} markets over {len(aligned_dates)} days")
    logger.debug(f"Final cumulative PnL: {final_pnl:.3f}")
    
    return PnlResult(
        cumulative_pnl=cumulative_pnl_points,
        final_pnl=final_pnl
    )









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

def get_all_markets_pnls():
    """Get PnL results for all agents using shared data loading approach."""
    from predibench.backend.leaderboard import _load_market_data, _calculate_agent_pnl_results
    
    market_data = _load_market_data()
    positions_df = market_data["positions_df"]
    prices_df = market_data["prices_df"]
    
    return _calculate_agent_pnl_results(positions_df, prices_df)
