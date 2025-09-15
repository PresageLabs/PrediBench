from datetime import datetime

import pandas as pd
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


# Test markets from late 2024 (about 6 months ago)
TEST_MARKETS = [
    {
        "id": "511754",
        "token_id": "103864131794756285503734468197278890131080300305704085735435172616220564121629",
        "question": "Will Zelenskyy wear a suit before July?",
        "start_date": "2025-05-25T12:00:00Z",
        "end_date": "2025-06-28T12:00:00Z",
    },
    {
        "id": "253597",
        "token_id": "69236923620077691027083946871148646972011131466059644796654161903044970987404",
        "question": "Will Kamala Harris win the 2024 US Presidential Election?",
        "end_date": "2024-02-04T12:00:00Z",
        "start_date": "2024-01-01T12:00:00Z",
    },
]


def test_market_request_for_old_closed_markets():
    """Test that MarketRequests can retrieve old closed markets from 6+ months ago."""
    # Create a request for closed markets from late 2024
    end_datetime_min = datetime(2025, 3, 1)
    end_datetime_max = datetime(2025, 7, 1)

    request_parameters = MarketsRequestParameters(
        limit=20,
        closed=True,
        active=False,
        end_date_min=end_datetime_min,
        end_date_max=end_datetime_max,
        order="volumeNum",
        ascending=False,
    )

    markets = request_parameters.get_markets()

    # Verify we got some markets
    assert len(markets) > 0, "Should find some closed markets from late 2024"

    # Verify all markets are closed and from the expected time period
    for market in markets[:3]:
        assert market.volume24hr is None or market.volume24hr == 0, (
            f"Market {market.id} should be inactive"
        )
        assert end_datetime_min <= market.end_datetime <= end_datetime_max, (
            f"Market {market.id} end date should be in expected range"
        )


def test_price_series_retrieval_over_several_months():
    """Test retrieving price series over several months for old closed markets."""

    for i, market_data in enumerate(TEST_MARKETS):
        print(f"\nTesting market {i + 1}: {market_data['question']}")

        end_datetime = datetime.fromisoformat(market_data["end_date"].replace("Z", ""))

        # Use the existing function with proper parameters
        timeseries_request_parameters = _HistoricalTimeSeriesRequestParameters(
            clob_token_id=market_data["token_id"],
            end_datetime=end_datetime,
        )

        # Use the method from the request object
        timeseries = timeseries_request_parameters.get_token_daily_timeseries()

        print(f"  Retrieved {len(timeseries)} data points")

        assert len(timeseries) > 0
        print(f"  Date range: {timeseries.index[0]} to {timeseries.index[-1]}")
        print(f"  Price range: {timeseries.min():.4f} to {timeseries.max():.4f}")
        print(f"  Final price: {timeseries.iloc[-1]:.4f}")

        # Verify we have reasonable amount of data
        assert len(timeseries) >= 1, (
            f"Should have at least 1 data point for market {market_data['id']}"
        )

        # Verify prices are reasonable (between 0 and 1 for prediction markets)
        for price in timeseries.values:
            assert 0 <= price <= 1, f"Price {price} should be between 0 and 1"

        # Verify data is a pandas Series
        assert isinstance(timeseries, pd.Series), "Should return pandas Series"


if __name__ == "__main__":
    test_polymarket_api_integration()
    test_get_open_markets()
    test_get_market_events()
    test_market_request_for_old_closed_markets()
    test_price_series_retrieval_over_several_months()
