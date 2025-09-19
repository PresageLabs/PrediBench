import json
from pathlib import Path

import pandas as pd
from predibench.agent.models import (
    ModelInfo,
    ModelInvestmentDecisions,
)
from predibench.backend.compute_profits import _compute_profits
from predibench.backend.data_model import (
    BackendData,
    EventBackend,
    FullModelResult,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import get_market_prices_dataframe
from predibench.common import DATA_PATH, PREFIX_MODEL_RESULTS
from predibench.logger_config import get_logger
from predibench.polymarket_api import Event, Market, load_market_price
from predibench.polymarket_data import load_events_from_file
from predibench.storage_utils import (
    _storage_using_bucket,
    file_exists_in_storage,
    get_bucket,
    read_from_storage,
)
from predibench.utils import _to_date_index, string_to_date

logger = get_logger(__name__)


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


def get_data_for_backend(
    recompute_bets_with_kelly_criterion: bool = False,
    ignored_providers: list[str] | None = None,
    custom_horizons: list[int] | None = None,
) -> BackendData:
    """
    Pre-compute all data needed for backend API endpoints.

    This function loads all data sources only once and computes everything needed
    for maximum performance at runtime.

    Args:
        recompute_bets_with_kelly_criterion: Whether to recompute all bets using Kelly criterion
        ignored_providers: List of provider names to ignore (case-insensitive)
    """
    logger.info("Starting comprehensive backend data computation...")

    # Step 1: Load all base data sources (load once, use everywhere)
    logger.info("Loading base data sources...")
    model_decisions = load_investment_choices_from_google()  # Load once

    # Filter out models from ignored providers
    if ignored_providers:
        ignored_providers_lower = [provider.lower() for provider in ignored_providers]
        original_count = len(model_decisions)
        model_decisions = [
            decision
            for decision in model_decisions
            if decision.model_info.inference_provider.lower()
            not in ignored_providers_lower
        ]
        filtered_count = len(model_decisions)
        logger.info(
            f"Filtered {original_count - filtered_count} model decisions from ignored providers: {ignored_providers}"
        )
        logger.info(f"Remaining model decisions: {filtered_count}")
    _saved_events = load_saved_events()  # Load once
    events = get_non_duplicated_events(_saved_events)
    logger.info("Loading market prices...")
    market_prices = load_market_prices(events)  # Load once
    prices_df = get_market_prices_dataframe(market_prices)  # Load once
    prices_df = prices_df.sort_index()
    # prices_df = prices_df.resample("D").last()  # Do this BEFORE _to_date_index
    prices_df = _to_date_index(prices_df)

    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]

    # Step 2: Optionally recompute bets using Kelly at decision time, then
    # compute ModelPerformanceBackend for each model
    logger.info("Computing model performance data (per day + per event)...")
    # When recomputing, apply Kelly using the original market price series
    # at the model's decision date; only bets are rescaled, unallocated stays.

    enriched_model_decisions, performance_per_model = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
        recompute_bets_with_kelly_criterion=recompute_bets_with_kelly_criterion,
        custom_horizons=custom_horizons,
    )

    # Step 3: Compute leaderboard from performance
    logger.info("Building leaderboard from performance data...")
    leaderboard = get_leaderboard(list(performance_per_model.values()))

    logger.info("Finished computing comprehensive backend data!")

    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance_per_model=performance_per_model,
        model_decisions=enriched_model_decisions,
    )


def load_event_decision_details_from_bucket(
    model_id: str, event_id: str, target_date: str
) -> FullModelResult | None:
    """Load a single full result from cache file."""
    model_result_path = ModelInfo.static_get_model_result_path(
        model_id=model_id, target_date=string_to_date(target_date)
    )
    cache_file_path = model_result_path / f"{event_id}_full_response.json"

    if file_exists_in_storage(cache_file_path):
        full_result_text = read_from_storage(cache_file_path)
        try:
            # First try to parse as FullModelResult (new format)
            result_data = json.loads(full_result_text)

            # Check if it's already a FullModelResult structure
            if isinstance(result_data, dict) and all(
                key in result_data
                for key in [
                    "model_id",
                    "event_id",
                    "target_date",
                    "full_result_listdict",
                ]
            ):
                # New format: directly parse as FullModelResult
                # Handle backward compatibility for files without agent_type field
                if "agent_type" not in result_data:
                    result_data["agent_type"] = None
                return FullModelResult.model_validate(result_data)
            else:
                # Old format: result_data is the raw full_result_listdict
                # Handle both list and dict formats and remove model_input_messages
                if isinstance(result_data, list):
                    # list format: remove model_input_messages from each step
                    for step in result_data:
                        if isinstance(step, dict) and "model_input_messages" in step:
                            del step["model_input_messages"]
                elif isinstance(result_data, dict):
                    # Dict format: remove model_input_messages if present
                    if "model_input_messages" in result_data:
                        del result_data["model_input_messages"]

            return FullModelResult(
                model_id=model_id,
                event_id=event_id,
                target_date=str(target_date),
                agent_type=None,  # Default for old files
                full_result_listdict=result_data,
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            # If parsing fails, return None
            return None
    return None


if __name__ == "__main__":
    get_data_for_backend()
