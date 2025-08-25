import os
from datetime import date, timedelta
from huggingface_hub import login
from dotenv import load_dotenv

import typer
from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from predibench.logger_config import get_logger
from predibench.retry_models import InferenceClientModelWithRetry, OpenAIModelWithRetry

logger = get_logger(__name__)

app = typer.Typer()

load_dotenv()
login(os.getenv("HF_TOKEN"))

MODEL_MAP = {
    "openai/gpt-5": OpenAIModelWithRetry(model_id="gpt-5"),
    "openai/gpt-5-mini": OpenAIModelWithRetry(model_id="gpt-5-mini"),
    "huggingface/openai/gpt-oss-120b": InferenceClientModelWithRetry(
        model_id="openai/gpt-oss-120b",
    ),
    "huggingface/openai/gpt-oss-20b": InferenceClientModelWithRetry(
        model_id="openai/gpt-oss-20b",
    ),
    "huggingface/deepseek-ai/DeepSeek-R1-0528": InferenceClientModelWithRetry(
        model_id="deepseek-ai/DeepSeek-R1-0528",
    ),
}


@app.command()
def main(
    max_events: int = typer.Option(5, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7 * 6, help="Days until event ending"),
    weeks_back: int = typer.Option(
        8, help="Number of weeks to go back for backward mode"
    ),
):
    """Main script to run investment analysis with all models across past weeks."""

    all_results = []

    logger.info("Starting investment analysis with all models across past weeks")

    # Generate dates for the past 4 weeks, starting with the oldest
    dates_to_process = []
    for week_offset in range(
        weeks_back, 0, -1
    ):  # Start from oldest (4 weeks back) to newest (1 week back)
        backward_date = date.today() - timedelta(weeks=week_offset)
        dates_to_process.append(backward_date)

    # Add today (no backward mode)
    dates_to_process.append(date.today())

    # Run for each date and each model
    for target_date in dates_to_process:
        is_today = target_date == date.today()
        target_date = None if is_today else target_date

        logger.info(
            f"Processing date: {target_date} ({'today' if is_today else 'backward mode'})"
        )

        run_investments_for_specific_date(
            time_until_ending=timedelta(days=days_ahead),
            max_n_events=max_events,
            models=list(MODEL_MAP.values()),  # Run one model at a time
            output_path=DATA_PATH,
            target_date=target_date,
            dataset_name="Sibyllic/predibench-2",
            split="train",
        )

    logger.info(f"All analyses completed. Total results: {len(all_results)}")


if __name__ == "__main__":
    app()
