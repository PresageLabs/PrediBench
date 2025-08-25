import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import login
from smolagents.models import (
    ApiModel,
)

from predibench.agent.runner import ModelInvestmentDecisions, run_agent_investments
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file
from predibench.retry_models import (
    InferenceClientModelWithRetry,
    OpenAIModelWithRetry,
)
from predibench.utils import get_timestamp_string
from predibench.storage_utils import file_exists_in_storage

load_dotenv()
login(os.getenv("HF_TOKEN"))

logger = get_logger(__name__)


def run_investments_for_specific_date(
    models: list[ApiModel | str],
    max_n_events: int,
    output_path: Path,
    time_until_ending: timedelta,
    target_date: date,
    cache_file_path: Path | None = None,
    force_rewrite_cache: bool = False,
    filter_crypto_events: bool = True,
    dataset_name: str = "Sibyllic/predibench-3",
    split: str = "train",
) -> list[ModelInvestmentDecisions]:
    """Run event-based investment simulation with multiple AI models."""
    logger.info(f"Running investment analysis for {target_date}")

    date_output_path = output_path / target_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    cache_file_path = (
        cache_file_path
        or date_output_path / f"events_cache_{get_timestamp_string()}.json"
    )

    if file_exists_in_storage(cache_file_path, force_rewrite=force_rewrite_cache):
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(cache_file_path)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            target_date=target_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events,
            filter_crypto_events=filter_crypto_events,
            save_path=cache_file_path,
        )

    logger.info(f"Selected {len(selected_events)} events:")
    for event in selected_events:
        logger.info(f"  - {event.title} (Volume: ${event.volume:,.0f})")

    for model in models:
        if isinstance(model, str):
            if model.startswith("openai/"):
                models[models.index(model)] = OpenAIModelWithRetry(
                    model_id=model[len("openai/") :]
                )
            elif model.startswith("huggingface/"):
                models[models.index(model)] = InferenceClientModelWithRetry(
                    model_id=model[len("huggingface/") :]
                )

    results = run_agent_investments(
        models=models,
        events=selected_events,
        target_date=target_date,
        date_output_path=date_output_path,
        dataset_name=dataset_name,
        split=split,
        timestamp_for_saving=get_timestamp_string(),
        force_rewrite_cache=force_rewrite_cache,
    )

    logger.info("Investment analysis complete!")

    return results


if __name__ == "__main__":
    # Test with random model to verify new output format
    models = [
        "huggingface/openai/gpt-oss-120b",  # Use test model for verification
        "huggingface/openai/gpt-oss-20b",  # Use test model for verification
    ]

    results = run_investments_for_specific_date(
        time_until_ending=timedelta(days=7 * 6),
        max_n_events=2,  # Smaller number for testing
        models=models,
        output_path=DATA_PATH,
        target_date=date(2025, 8, 19),
    )
