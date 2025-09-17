import os
from datetime import date, timedelta, datetime
from typing import List

import typer
from dotenv import load_dotenv
from huggingface_hub import login
from predibench.agent.models import ModelInfo
from predibench.invest import run_investments_for_specific_date
from predibench.logger_config import get_logger

logger = get_logger(__name__)

app = typer.Typer()

load_dotenv()
login(os.getenv("HF_TOKEN"))

BACKWARD_MODE_MODELS = [
    ModelInfo(
        model_id="test_random",
        model_pretty_name="Random Baseline",
        inference_provider="baseline",
        company_pretty_name="Baseline",
    ),
    ModelInfo(
        model_id="most_likely_outcome",
        model_pretty_name="Most Likely Outcome",
        inference_provider="baseline",
        company_pretty_name="Baseline",
    ),
    ModelInfo(
        model_id="most_likely_volume_proportional",
        model_pretty_name="Volume Proportional",
        inference_provider="baseline",
        company_pretty_name="Baseline",
    ),
]


@app.command()
def main(
    max_events: int = typer.Option(10, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7 * 6, help="Days until event ending"),
    dates: List[str] = typer.Option(help="List of dates to process (YYYY-MM-DD format)"),
):
    """Main script to run investment analysis with all models for specified dates."""

    logger.info(f"Starting investment analysis for dates: {dates}")

    # Parse dates
    dates_to_process = []
    for date_str in dates:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        dates_to_process.append(parsed_date)

    # Run for each date and each model
    for target_date in dates_to_process:
        run_investments_for_specific_date(
            time_until_ending=timedelta(days=days_ahead),
            max_n_events=max_events,
            models=BACKWARD_MODE_MODELS,  # Run one model at a time
            target_date=target_date,
        )

    logger.info("All analyses completed")


if __name__ == "__main__":
    main(
        days_ahead=7 * 6,
        max_events=10,
        dates=["2025-08-29", "2025-09-01", "2025-09-03", "2025-09-05", "2025-09-08", "2025-09-10", "2025-09-12", "2025-09-15"],
    )
    pass
