import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import login

from predibench.agent.dataclasses import ModelInfo
from predibench.agent.runner import ModelInvestmentDecisions, run_agent_investments
from predibench.common import DATA_PATH, get_date_output_path
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file
from predibench.retry_models import (
    InferenceClientModelWithRetry,
    OpenAIModelWithRetry,
)
from predibench.storage_utils import file_exists_in_storage
from predibench.utils import get_timestamp_string

load_dotenv(override=True)
login(os.getenv("HF_TOKEN"))

logger = get_logger(__name__)


def run_investments_for_specific_date(
    models: list[ModelInfo],
    max_n_events: int,
    target_date: date,
    time_until_ending: timedelta,
    force_rewrite: bool = False,
    filter_crypto_events: bool = True,
) -> list[ModelInvestmentDecisions]:
    """Run event-based investment simulation with multiple AI models."""
    logger.info(f"Running investment analysis for {target_date}")

    cache_file_path = get_date_output_path(target_date)
    cache_file_path = cache_file_path / "events.json"

    if file_exists_in_storage(cache_file_path, force_rewrite=force_rewrite):
        logger.info(f"Loading events from cache: {cache_file_path}")
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
        if model.inference_provider == "openai":
            model.client = OpenAIModelWithRetry(model_id=model.model_id)
        elif model.inference_provider == "anthropic":
            # NOTE: Use bedrock in case
            model.client = OpenAIModelWithRetry(model_id=model.model_id)
        elif model.open_weights:
            model.client = InferenceClientModelWithRetry(
                model_id=model.model_id,
                provider=model.inference_provider,
            )

    results = run_agent_investments(
        models=models,
        events=selected_events,
        target_date=target_date,
        force_rewrite=force_rewrite,
    )

    logger.info("Investment analysis complete!")

    return results


if __name__ == "__main__":
    # Test with random model to verify new output format
    models = [
        ModelInfo(
        model_id="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        model_pretty_name="Qwen3-Coder-480B-A35B-Instruct",
        inference_provider="fireworks-ai",
        company_pretty_name="Qwen",
        open_weights=True,
    ),
        ModelInfo(
            model_id="openai/gpt-oss-120b",
            model_pretty_name="GPT-OSS 120B",
            inference_provider="fireworks-ai",
            company_pretty_name="OpenAI",
            open_weights=True,
        ),
    ]

    results = run_investments_for_specific_date(
        models=models,
        time_until_ending=timedelta(days=7 * 6),
        max_n_events=2,
        target_date=date(2025, 8, 19),
        force_rewrite=True,
    )
