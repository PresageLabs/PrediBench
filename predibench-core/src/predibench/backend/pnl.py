from datetime import date
import numpy as np
import pandas as pd

from predibench.backend.data_loader import load_agent_position
from predibench.logger_config import get_logger
from predibench.backend.data_model import PnlResult, DataPoint

logger = get_logger(__name__)


def _assert_index_is_date(df: pd.DataFrame):
    assert all(isinstance(idx, date) for idx in df.index), (
        "All index values must be date objects or timestamps without time component"
    )


# Removed unused _get_positions_begin_next_day function


def calculate_pnl(
    positions_agent_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> PnlResult:
    """
    Calculate profit and loss for given positions and prices.
    
    For each market, PnL is calculated from first agent bet until market end:
    - Start: First non-NaN position in positions_agent_df for that market
    - End: Last non-NaN price in prices_df for that market
    - PnL = position_held_yesterday * (price_today - price_yesterday)
    
    Args:
        positions_agent_df: Daily positions DataFrame with dates as index, markets as columns
        prices_df: Price data DataFrame with dates as index, markets as columns
        
    Returns:
        PnlResult with cumulative PnL time series and final value
    """
    _assert_index_is_date(positions_agent_df)
    _assert_index_is_date(prices_df)
    
    # Calculate PnL for each market individually
    market_pnl_series = {}
    
    for market_id in positions_agent_df.columns:
        if market_id not in prices_df.columns:
            logger.warning(f"Market {market_id} not found in prices data, skipping")
            continue
            
        # Get agent positions and market prices for this market
        agent_positions_series = positions_agent_df[market_id]
        market_prices_raw = prices_df[market_id]
        
        # Interpolate missing prices between non-NaN values
        market_prices = market_prices_raw.interpolate(method='linear').dropna()
        
        # Find first and last non-NaN positions (but keep the series intact)
        valid_positions = agent_positions_series.dropna()
        if len(valid_positions) == 0 or len(market_prices) == 0:
            logger.debug(f"No valid data for market {market_id}, skipping")
            continue
        
        # Find the date range for this market:
        # Start: First non-NaN agent position
        # End: Last non-NaN market price  
        first_bet_date = valid_positions.index.min()
        last_market_date = market_prices.index.max()
        
        if first_bet_date > last_market_date:
            raise ValueError(f"Agent started betting after market {market_id} ended")
            
        # Create date range for this market's PnL calculation
        market_date_range = pd.date_range(start=first_bet_date, end=last_market_date, freq='D')
        # Convert to date objects to match our data format
        market_date_range = pd.Index([d.date() for d in market_date_range])
        market_date_range = market_date_range.intersection(market_prices.index)
        
        if len(market_date_range) == 0:
            logger.debug(f"No overlapping dates for market {market_id}, skipping")
            continue
        
        # Extend agent positions to cover the full market duration
        # Forward-fill positions: NaN means "hold previous position"
        extended_positions = agent_positions_series.reindex(market_date_range).ffill().fillna(0)
        
        # Get aligned prices and calculate price changes
        aligned_prices = market_prices.reindex(market_date_range, method='ffill')
        price_changes = aligned_prices.diff().fillna(0)
        
        # Calculate daily PnL: previous_day_position * price_change
        # First day has no previous position, so PnL starts from second day
        daily_pnl = extended_positions.shift(1, fill_value=0) * price_changes
        
        market_pnl_series[market_id] = daily_pnl
        
        logger.debug(f"Market {market_id}: PnL from {first_bet_date} to {last_market_date}")
    
    if not market_pnl_series:
        logger.warning("No valid market PnL data calculated")
        return PnlResult(cumulative_pnl=[], final_pnl=0.0)
    
    # Combine all market PnLs into a unified timeline
    # Get all dates from all markets
    all_dates = set()
    for pnl_series in market_pnl_series.values():
        all_dates.update(pnl_series.index)
    
    all_dates = sorted(all_dates)
    
    # Calculate portfolio daily PnL by summing across markets for each date
    portfolio_daily_pnl = pd.Series(0.0, index=all_dates)
    
    for market_id, market_pnl in market_pnl_series.items():
        # Align each market's PnL to the full timeline
        aligned_market_pnl = market_pnl.reindex(all_dates, fill_value=0.0)
        portfolio_daily_pnl += aligned_market_pnl
    
    # Calculate cumulative PnL
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
    
    logger.info(f"Calculated PnL for {len(market_pnl_series)} markets over {len(all_dates)} total days")
    logger.info(f"Final cumulative PnL: {final_pnl:.3f}")
    
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
