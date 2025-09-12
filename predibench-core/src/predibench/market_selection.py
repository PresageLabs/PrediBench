from datetime import date, datetime, timedelta
from pathlib import Path

from predibench.date_utils import is_backward_mode
from predibench.logger_config import get_logger
from predibench.polymarket_api import (
    Event,
    EventsRequestParameters,
)
from predibench.polymarket_data import save_events_to_file

logger = get_logger(__name__)


def _remove_markets_without_prices_in_events(events: list[Event]) -> list[Event]:
    """Remove markets that have no prices"""
    filtered_events = []
    for event in events:
        market_filtered = [
            market
            for market in event.markets
            if market.prices is not None and len(market.prices) >= 1
        ]
        event.markets = market_filtered
        if len(market_filtered) > 0:
            filtered_events.append(event)
    return filtered_events


def _filter_crypto_events(events: list[Event]) -> list[Event]:
    """Filter out events related to crypto by checking if 'bitcoin' or 'ethereum' is in the slug."""
    crypto_keywords = ["bitcoin", "ethereum", "xrp", "solana", "eth", "btc"]
    filtered_events = []

    for event in events:
        slug_lower = event.slug.lower() if event.slug else ""
        is_crypto = any(keyword in slug_lower for keyword in crypto_keywords)

        if not is_crypto:
            filtered_events.append(event)
        else:
            logger.info(
                f"Filtered out crypto event: {event.title} (slug: {event.slug})"
            )

    return filtered_events


def _filter_events_by_volume_and_markets(
    events: list[Event], min_volume: float = 1000, backward_mode: bool = False
) -> list[Event]:
    """Filter events based on volume threshold and presence of markets."""
    filtered_events = []
    for event in events:
        if event.markets and len(event.markets) > 0:
            if backward_mode:
                # In backward mode, we can't rely on volume24hr as it may not be available for historical events
                # Just ensure events have markets
                filtered_events.append(event)
            elif (
                event.volume24hr and event.volume24hr > min_volume
            ):  # Minimum volume threshold
                filtered_events.append(event)
    return filtered_events


def _select_markets_for_events(
    events: list[Event], base_date: date, backward_mode: bool = False
) -> list[Event]:
    """Keep all relevant markets for each event instead of selecting just one."""

    if backward_mode:
        events_with_markets = []
        for event in events:
            # Filter events where end_date is after base_date, or keep if end_date doesn't exist
            if event.end_datetime is None or event.end_datetime.date() > base_date:
                # Filter markets that are still active
                eligible_markets = [
                    market
                    for market in event.markets
                    if market.end_datetime is None
                    or market.end_datetime.date() > base_date
                ]

                if eligible_markets:
                    event.markets = eligible_markets  # Keep all eligible markets
                    events_with_markets.append(event)

                    end_date_str = (
                        event.end_datetime.date()
                        if event.end_datetime
                        else "no end date"
                    )
                    logger.info(
                        f"Backward mode: Selected event '{event.title}' ending {end_date_str} with {len(eligible_markets)} markets"
                    )

        return events_with_markets

    events_with_markets = []
    for event in events:
        eligible_markets = []
        for market in event.markets:
            if market.outcomes and len(market.outcomes) > 0:
                eligible_markets.append(market)

        if eligible_markets:
            event.markets = eligible_markets  # Keep all eligible markets
            events_with_markets.append(event)
            logger.info(
                f"Event '{event.title}' has {len(eligible_markets)} eligible markets"
            )

    return events_with_markets


def choose_events(
    target_date: date,
    time_until_ending: timedelta,
    n_events: int,
    min_volume: float = 1000,
    filter_crypto_events: bool = True,
    save_path: Path | None = None,
) -> list[Event]:
    """Pick top events by volume for investment for the current week
    if True, then events ending around this date will be selected, but those events are probably closed, we can't use the volume24hr to filter out the events that are open.

    """
    backward_mode = is_backward_mode(target_date)
    end_date = target_date + time_until_ending
    start_datetime, end_datetime = (
        datetime.combine(target_date, datetime.min.time()),
        datetime.combine(end_date, datetime.min.time()),
    )
    request_parameters = EventsRequestParameters(
        limit=500,
        order="volume" if backward_mode else "volume1wk",
        ascending=False,
        closed=None if backward_mode else False,
        end_date_min=start_datetime if backward_mode else None,
        end_date_max=end_datetime,
    )
    events = request_parameters.get_events()

    if filter_crypto_events:
        events = _filter_crypto_events(events)

    filtered_events = _filter_events_by_volume_and_markets(
        events=events, min_volume=min_volume, backward_mode=backward_mode
    )
    filtered_events = filtered_events[
        : n_events + int(n_events + 3)
    ]  # NOTE: a few events might be missing prices and will be removed later so we add a few more events to be sure to have enough

    for event in filtered_events:
        for market in event.markets:
            if backward_mode:
                market.fill_prices(end_datetime=end_datetime)
            else:
                market.fill_prices()

    filtered_events = _remove_markets_without_prices_in_events(filtered_events)

    events_with_selected_markets = _select_markets_for_events(
        events=filtered_events, base_date=target_date, backward_mode=backward_mode
    )
    events_with_selected_markets = events_with_selected_markets[:n_events]
    if save_path is not None:
        save_events_to_file(events=events_with_selected_markets, file_path=save_path)

    if len(events_with_selected_markets) < n_events:
        raise ValueError(
            f"Only {len(events_with_selected_markets)} events were selected, expected {n_events}"
        )
    return events_with_selected_markets
