from datetime import date, datetime, timedelta

import pandas as pd
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file, save_events_to_file
from predibench.storage_utils import file_exists_in_storage, delete_from_storage

logger = get_logger(__name__)


def test_choose_events_event_caching_e2e():
    """End-to-end test for event save/load functionality."""

    # Test parameters (same as used in invest.py)
    today_date = date.today()
    event_selection_window = timedelta(days=6 * 7)
    max_n_events = 3

    # Step 1: Fetch events from API
    selected_events = choose_events(
        target_date=today_date,
        time_until_ending=event_selection_window,
        n_events=max_n_events,
    )

    # checking events
    nb_markets_with_prices = 0
    nb_markets_with_many_prices = 0
    nb_markets_without_prices = 0
    assert len(selected_events) == max_n_events, (
        f"Expected {max_n_events} events, got {len(selected_events)}"
    )
    for event in selected_events:
        assert len(event.markets) > 0, f"Event {event.title} has no markets"
        assert event.volume24hr is not None, f"Event {event.title} has no volume24hr"
        assert event.volume24hr > 0, f"Event {event.title} has no volume24hr"
        assert event.end_datetime.date() <= today_date + event_selection_window, (
            f"Event {event.title} has end_date {event.end_datetime} which is after {today_date + event_selection_window}"
        )

        for market in event.markets:
            assert len(market.outcomes) == 2, (
                f"Market {market.question} has {len(market.outcomes)} outcomes, expected 2"
            )
            if market.prices is not None and len(market.prices) >= 1:
                nb_markets_with_prices += 1
                if len(market.prices) > 2:
                    nb_markets_with_many_prices += 1
            else:
                nb_markets_without_prices += 1
    assert (
        nb_markets_with_prices > 3
    )  # NOTE: There are 3 events, so at least 3 markets should have prices
    assert nb_markets_without_prices == 0
    assert (
        nb_markets_with_many_prices >= nb_markets_with_prices * 0.5
    )  # NOTE: this test might fail depending on the date, for instance if this is a very new event but it should be enough
    # Step 2: Save events to file
    cache_file = DATA_PATH / "test_events_cache.json"
    save_events_to_file(selected_events, cache_file)

    # Verify file was created - file_exists_in_storage works for both modes
    assert file_exists_in_storage(cache_file), f"Cache file was not created: {cache_file}"

    # Step 3: Load events from file
    loaded_events = load_events_from_file(cache_file)

    # Step 4: Verify data integrity
    # Check basic counts
    assert len(selected_events) == len(loaded_events), (
        f"Event count mismatch: original={len(selected_events)}, loaded={len(loaded_events)}"
    )

    # Check each event
    for i, (original, loaded) in enumerate(zip(selected_events, loaded_events)):
        # Check basic event properties
        assert original.id == loaded.id, f"Event ID mismatch for event {i}"
        assert original.title == loaded.title, f"Event title mismatch for event {i}"
        assert original.slug == loaded.slug, f"Event slug mismatch for event {i}"
        assert original.description == loaded.description, (
            f"Event description mismatch for event {i}"
        )

        # Check numeric fields
        assert original.volume == loaded.volume, f"Event volume mismatch for event {i}"
        assert original.volume24hr == loaded.volume24hr, (
            f"Event volume24hr mismatch for event {i}"
        )
        assert original.liquidity == loaded.liquidity, (
            f"Event liquidity mismatch for event {i}"
        )

        # Check markets count
        assert len(original.markets) == len(loaded.markets), (
            f"Markets count mismatch for event {i}: original={len(original.markets)}, loaded={len(loaded.markets)}"
        )

        # Check first market details (if exists)
        if original.markets and loaded.markets:
            orig_market = original.markets[0]
            loaded_market = loaded.markets[0]

            assert orig_market.id == loaded_market.id, (
                f"Market ID mismatch for event {i}"
            )
            assert orig_market.question == loaded_market.question, (
                f"Market question mismatch for event {i}"
            )
            assert len(orig_market.outcomes) == len(loaded_market.outcomes), (
                f"Market outcomes count mismatch for event {i}"
            )

            # Check pandas Series prices preservation
            if orig_market.prices is not None:
                assert loaded_market.prices is not None, (
                    f"Prices Series lost during serialization for market {orig_market.id}"
                )
                assert isinstance(loaded_market.prices, pd.Series), (
                    f"Prices should be a pandas Series for market {orig_market.id}"
                )
                assert orig_market.prices.name == loaded_market.prices.name, (
                    f"Series name mismatch for market {orig_market.id}"
                )
                assert len(orig_market.prices) == len(loaded_market.prices), (
                    f"Series length mismatch for market {orig_market.id}"
                )

                # Check that values are preserved (index may be converted to DatetimeIndex)
                assert list(orig_market.prices.values) == list(
                    loaded_market.prices.values
                ), f"Values mismatch for market {orig_market.id}"
                assert len(orig_market.prices) == len(loaded_market.prices), (
                    f"Length mismatch for market {orig_market.id}"
                )
                # Convert both to DatetimeIndex for comparison
                orig_dt_index = pd.to_datetime(orig_market.prices.index)
                loaded_dt_index = pd.to_datetime(loaded_market.prices.index)
                assert list(orig_dt_index) == list(loaded_dt_index), (
                    f"Index mismatch for market {orig_market.id}"
                )
            else:
                assert loaded_market.prices is None, (
                    f"Prices should be None for market {orig_market.id}"
                )

    # Step 5: Cleanup - delete_from_storage works for both modes
    delete_from_storage(cache_file)


def test_choose_events_backward():
    """Test choose_events function for backward mode."""
    # Test parameters
    base_datetime = datetime(2024, 8, 15)  # Fixed date for testing

    event_selection_window = timedelta(days=6 * 7)
    max_n_events = 3

    # Test 1: Normal mode (backward_mode=False)
    selected_events = choose_events(
        target_date=base_datetime.date(),
        time_until_ending=event_selection_window,
        n_events=max_n_events,
    )

    # checking events
    nb_markets_with_prices = 0
    nb_markets_without_prices = 0
    assert len(selected_events) > 0, (
        f"Expected {max_n_events} events, got {len(selected_events)}"
    )
    for event in selected_events:
        assert len(event.markets) > 0, f"Event {event.title} has no markets"
        assert event.end_datetime <= base_datetime + event_selection_window, (
            f"Event {event.title} has end_date {event.end_datetime} which is after {base_datetime + event_selection_window}"
        )

        for market in event.markets:
            assert len(market.outcomes) == 2, (
                f"Market {market.question} has {len(market.outcomes)} outcomes, expected 2"
            )
            if (
                market.prices is not None and len(market.prices) > 10
            ):  # NOTE: this should be enough
                nb_markets_with_prices += 1
            else:
                nb_markets_without_prices += 1
    assert nb_markets_with_prices > 0


def main():
    test_choose_events_event_caching_e2e()
    test_choose_events_backward()


if __name__ == "__main__":
    main()
