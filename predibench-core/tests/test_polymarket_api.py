from datetime import datetime

from predibench.polymarket_api import (
    EventsRequestParameters,
    MarketsRequestParameters,
    _HistoricalTimeSeriesRequestParameters,
)


def test_get_open_markets():
    """Test basic market retrieval."""
    request_parameters = MarketsRequestParameters(limit=10)
    markets = request_parameters.get_markets()
    for market in markets:
        assert len(market.outcomes) >= 2
    # why not 500 ? Some markets are missing keys clobTokenIds or outcomes
    assert len(markets) == 10
    for market in markets:
        assert len(market.id) > 0
        assert len(market.question) > 0
        assert market.liquidity is None or market.liquidity >= 0


def test_polymarket_api_integration():
    """Test the complete Polymarket API workflow with live data."""
    # Fetch active markets
    market_request = MarketsRequestParameters(
        limit=5,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        liquidity_num_min=1000,
    )
    all_markets = market_request.get_markets()

    # Verify we got markets and find an open one
    assert len(all_markets) > 0, "Should find some active markets"

    open_market = None
    for market in all_markets:
        print(
            f"Checking market: {market.question[:50]}... (created: {market.creation_datetime.year})"
        )
        if market.volume24hr > 0:
            open_market = market
            break

    assert open_market is not None, "No open market found"

    # Verify market properties
    assert len(open_market.id) > 0
    assert len(open_market.question) > 0
    assert len(open_market.outcomes) >= 2

    print(f"\nUsing market: {open_market.question}")
    print(f"Created: {open_market.creation_datetime}")

    # Test order book functionality
    token_id = open_market.outcomes[0].clob_token_id
    print(f"\nGetting order book for token: {token_id}")

    order_book = OrderBook.get_order_book(token_id)

    # Verify order book structure
    assert len(order_book.market) > 0
    assert len(order_book.asset_id) > 0
    assert len(order_book.timestamp) > 0
    assert isinstance(order_book.bids, list)
    assert isinstance(order_book.asks, list)

    print(f"Order book timestamp: {order_book.timestamp}")
    print(f"Best bid: {order_book.bids[0].price if order_book.bids else 'None'}")
    print(f"Best ask: {order_book.asks[0].price if order_book.asks else 'None'}")
    print(f"Tick size: {order_book.tick_size}")

    # Test timeseries functionality
    timeseries_request_parameters = _HistoricalTimeSeriesRequestParameters(
        clob_token_id=token_id,
        end_datetime=datetime.now(),
    )
    timeseries = timeseries_request_parameters.get_token_daily_timeseries()

    # Verify timeseries data
    assert len(timeseries) > 0, "Should have some timeseries data"
    assert all(0 <= price <= 1 for price in timeseries.values), (
        "Prices should be between 0 and 1"
    )

    print(f"Found {len(timeseries)} data points")
    for date, price in timeseries.iloc[-5:].items():  # Print last 5 points
        print(f"  {date}: ${price:.4f}")


def test_get_market_events():
    """Test basic market event retrieval."""
    request_first = EventsRequestParameters(limit=5)
    events = request_first.get_events()
    assert len(events) == 5

    for event in events:
        # Basic validation of event properties
        assert len(event.id) > 0
        assert len(event.slug) > 0
        assert len(event.title) > 0
        assert event.liquidity is None or event.liquidity >= 0
        assert event.volume is None or event.volume >= 0
        assert event.start_datetime is None or isinstance(
            event.start_datetime, datetime
        )
        assert event.end_datetime is None or isinstance(event.end_datetime, datetime)
        assert isinstance(event.creation_datetime, datetime)
        assert isinstance(event.markets, list)

        # Validate markets structure
        for market in event.markets:
            assert len(market.id) > 0
            assert len(market.question) > 0
            assert len(market.outcomes) >= 2
            assert isinstance(market.outcomes, list)
            # Validate market outcomes
            for outcome in market.outcomes:
                assert len(outcome.name) > 0
                assert len(outcome.clob_token_id) > 0
                assert 0 <= outcome.price <= 1

    assert len(events) >= 1  # Should get at least some events

    # Test offset
    request_second = EventsRequestParameters(limit=5, offset=5)
    events_second = request_second.get_events()
    assert len(events_second) == 5

    first_ids = {event.id for event in events}
    second_ids = {event.id for event in events_second}
    # Events should be different (though not necessarily disjoint due to API behavior)
    assert len(first_ids.union(second_ids)) > len(first_ids)


if __name__ == "__main__":
    test_polymarket_api_integration()
    test_get_open_markets()
    test_get_market_events()
