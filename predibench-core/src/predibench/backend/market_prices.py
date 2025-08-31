from functools import lru_cache
from predibench.polymarket_api import _HistoricalTimeSeriesRequestParameters
from predibench.backend.events import get_events_by_ids


def get_event_market_prices(event_id: str):
    """Get price history for all markets in an event"""
    events_list = get_events_by_ids((event_id,))

    if not events_list:
        return {}

    event = events_list[0]
    market_prices = {}

    # Get prices for each market in the event
    for market in event.markets:
        clob_token_id = market.outcomes[0].clob_token_id
        price_data = _HistoricalTimeSeriesRequestParameters(
            clob_token_id=clob_token_id,
        ).get_cached_token_timeseries()

        market_prices[market.id] = price_data

    return market_prices