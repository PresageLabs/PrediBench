from datetime import datetime, timezone

from predibench.polymarket_api import MarketsRequestParameters, _HistoricalTimeSeriesRequestParameters
from predibench.storage_utils import delete_from_storage


def test_cached_timeseries_functionality():
    """Test the cached timeseries functionality end-to-end."""
    # Get a real market with active trading
    market_request = MarketsRequestParameters(
        limit=500,
        order="volume24hr",
        ascending=False,
    )
    markets = market_request.get_markets(fill_prices=False)
    
    # Find a market with valid token ID
    test_market = None
    for market in markets:
        if market.outcomes and len(market.outcomes) >= 2 and market.outcomes[0].clob_token_id:
            test_market = market
            break
    
    assert test_market is not None, "Could not find a suitable market for testing"
    
    token_id = test_market.outcomes[0].clob_token_id
    print(f"Testing with market: {test_market.question[:50]}...")
    print(f"Token ID: {token_id}")
    
    # Create timeseries request
    ts_request = _HistoricalTimeSeriesRequestParameters(
        clob_token_id=token_id,
        end_datetime=datetime.now(timezone.utc)
    )
    
    # Clean up any existing cache
    cache_path = ts_request._get_cache_path()
    delete_from_storage(cache_path)
    
    # Test 1: First call should fetch and cache data
    timeseries1 = ts_request.get_cached_token_timeseries()
    assert timeseries1 is not None
    assert len(timeseries1) > 0
    assert cache_path.exists(), "Cache file should be created"
    
    # Test 2: Second call should use cached data
    timeseries2 = ts_request.get_cached_token_timeseries()
    assert timeseries2 is not None
    assert len(timeseries2) == len(timeseries1)
    
    # Test 3: Update should work
    updated_timeseries = ts_request.update_cached_token_timeseries()
    assert updated_timeseries is not None
    assert len(updated_timeseries) >= len(timeseries1)
    
    # Test 4: Market fill_prices should use cached version
    test_market.fill_prices()
    assert test_market.prices is not None
    assert len(test_market.prices) > 0
    
    # Clean up
    delete_from_storage(cache_path)
    
    print("✓ All caching functionality tests passed")
    
if __name__ == "__main__":
    test_cached_timeseries_functionality()