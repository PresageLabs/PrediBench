from functools import lru_cache
from predibench.agent.dataclasses import ModelInvestmentDecisions
from predibench.polymarket_data import load_events_from_file
from predibench.storage_utils import get_bucket
from predibench.common import DATA_PATH
from pathlib import Path


@lru_cache(maxsize=1)
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
    return model_results

def get_market_to_clob() -> dict[str, str]:
    """
    The cached data for the markets is saved by clob id. But the results are saved by market id.
    This function will return a dictionary that maps market id to clob id.
    
    A better way to do this would be to save the clob id in the results.
    """
    bucket = get_bucket()
    blobs = bucket.list_blobs(prefix="")
    market_to_clob = {}
    for blob in blobs:
        if blob.name.endswith("events.json"):
            file_path = DATA_PATH / Path(blob.name)
            events = load_events_from_file(file_path)
            for event in events:
                for market in event.markets:
                    market_to_clob[market.id] = market.outcomes[0].clob_token_id
    return market_to_clob
    

@lru_cache(maxsize=1)
def load_agent_choices():
    """Load agent choices from GCP instead of HuggingFace dataset"""
    return load_investment_choices_from_google()
