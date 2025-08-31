from functools import lru_cache
from predibench.agent.dataclasses import ModelInvestmentDecisions
from predibench.polymarket_api import load_market_price, Market, Event
from predibench.polymarket_data import load_events_from_file
from predibench.storage_utils import get_bucket
from predibench.common import DATA_PATH
from pathlib import Path
import pandas as pd


def load_investment_choices_from_google() -> list[ModelInvestmentDecisions]:
    # Has bucket access, load directly from GCP bucket

    model_results = []
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix="")

    for blob in blobs:
        if (
            blob.name.endswith("model_investment_decisions.json")
        ):
            try:
                json_content = blob.download_as_text()
                model_result = ModelInvestmentDecisions.model_validate_json(
                    json_content
                )
                model_results.append(model_result)
            except Exception as e:
                print(f"Error reading {blob.name}: {e}")
                continue

    # Sort by target_date
    model_results.sort(key=lambda x: x.target_date)
    
    # Very important:Normalize gains for all event decisions
    for model_result in model_results:
        for event_decision in model_result.event_investment_decisions:
            event_decision.normalize_gains()
    return model_results

def load_saved_events() -> list[Event]:
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix="")
    events = []
    for blob in blobs:
        if blob.name.endswith("events.json"):
            file_path = DATA_PATH / Path(blob.name)
            events = load_events_from_file(file_path)
            events.extend(events)
    return events

def load_market_prices(events: list[Event]) -> dict[str, pd.Series | None]:
    """
    The cached data for the markets is saved by clob id. But the results are saved by market id.
    This function will return a dictionary that maps market id to clob id.
    
    A better way to do this would be to save the clob id in the results.
    """
    market_to_prices = {}
    for event in events:
        for market in event.markets:
            market_prices = load_market_price(market.outcomes[0].clob_token_id)
            market_to_prices[market.id] = Market.convert_to_daily_data(market_prices)
    return market_to_prices
    


def load_agent_position(model_results: list[ModelInvestmentDecisions]) -> pd.DataFrame:
    """Load agent choices from GCP instead of HuggingFace dataset"""
    
    print(f"Loaded {len(model_results)} model results from GCP")

    positions = []
    for model_result in model_results:
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
                        "model_id": model_result.model_id,
                        "odds": market_decision.model_decision.odds,
                        "confidence": market_decision.model_decision.confidence,
                    }
                )

    positions_df = pd.DataFrame.from_records(positions)
    print(f"Created {len(positions_df)} position records")
    return positions_df
