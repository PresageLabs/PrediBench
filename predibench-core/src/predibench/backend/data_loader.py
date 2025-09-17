from pathlib import Path

import pandas as pd
from predibench.agent.models import ModelInvestmentDecisions
from predibench.common import DATA_PATH, PREFIX_MODEL_RESULTS
from predibench.polymarket_api import Event, Market, load_market_price
from predibench.polymarket_data import load_events_from_file
from predibench.storage_utils import _storage_using_bucket, get_bucket


def load_investment_choices_from_google() -> list[ModelInvestmentDecisions]:
    # Has bucket access, load directly from GCP bucket

    model_results: list[ModelInvestmentDecisions] = []
    if _storage_using_bucket():
        bucket = get_bucket()
        blobs = bucket.list_blobs(prefix=PREFIX_MODEL_RESULTS)

        for blob in blobs:
            if blob.name.endswith("model_investment_decisions.json"):
                try:
                    json_content = blob.download_as_text()
                    model_result = ModelInvestmentDecisions.model_validate_json(
                        json_content
                    )
                    model_results.append(model_result)
                except Exception as e:
                    print(f"Error reading {blob.name}: {e}")
                    continue
    else:
        # Fallback to local files when bucket is not available
        for file_path in DATA_PATH.rglob("*.json"):
            if file_path.name == "model_investment_decisions.json":
                try:
                    with open(file_path, "r") as f:
                        json_content = f.read()
                    model_result = ModelInvestmentDecisions.model_validate_json(
                        json_content
                    )
                    model_results.append(model_result)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

    # Sort by target_date
    model_results.sort(key=lambda x: x.target_date)

    # Very important: Normalize gains for all event decisions
    for model_result in model_results:
        for event_decision in model_result.event_investment_decisions:
            event_decision.normalize_investments()
    return model_results


def load_saved_events() -> list[Event]:
    all_events: list[Event] = []

    if _storage_using_bucket():
        # Load from bucket
        bucket = get_bucket()
        if bucket is not None:
            blobs = bucket.list_blobs(prefix=PREFIX_MODEL_RESULTS)
            for blob in blobs:
                if blob.name.endswith("events.json"):
                    file_path = DATA_PATH / Path(blob.name)
                    loaded = load_events_from_file(file_path)
                    all_events.extend(loaded)
    else:
        # Fallback to local files when bucket is not available
        for file_path in DATA_PATH.rglob("*.json"):
            if file_path.name == "events.json":
                try:
                    loaded = load_events_from_file(file_path)
                    all_events.extend(loaded)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

    return all_events


def load_market_prices(events: list[Event]) -> dict[str, pd.Series | None]:
    """
    The cached data for the markets is saved by clob id. But the results are saved by market id.
    This function will return a dictionary that maps market id to clob id.

    A better way to do this would be to save the clob id in the results.
    """
    market_to_prices = {}
    for event in events:
        for market in event.markets:
            if market.id not in market_to_prices:
                market_prices = load_market_price(market.outcomes[0].clob_token_id)
                market_prices = Market.convert_to_daily_data(market_prices)
                market.prices = market_prices
                market_to_prices[market.id] = market_prices
            else:
                market.prices = market_to_prices[market.id]

    return market_to_prices
