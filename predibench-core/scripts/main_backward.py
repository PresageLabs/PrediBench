import os
from datetime import date, timedelta
from huggingface_hub import login
from dotenv import load_dotenv
from predibench.agent.dataclasses import ModelInfo

import typer
from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from predibench.logger_config import get_logger
from predibench.retry_models import InferenceClientModelWithRetry, OpenAIModelWithRetry

logger = get_logger(__name__)

app = typer.Typer()

load_dotenv()
login(os.getenv("HF_TOKEN"))

BACKWARD_MODE_MODELS = [
        ModelInfo(
        model_id="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        model_pretty_name="Qwen3-Coder-480B-A35B-Instruct",
        inference_provider="fireworks-ai",
        company_pretty_name="Qwen",
        open_weights=True,
        agent_type="codeagent",
    ),
        ModelInfo(
            model_id="openai/gpt-oss-120b",
            model_pretty_name="GPT-OSS 120B",
            inference_provider="fireworks-ai",
            company_pretty_name="OpenAI",
            open_weights=True,
            agent_type="toolcalling",
        ),
        ModelInfo(
        model_id="deepseek-ai/DeepSeek-V3.1",
        model_pretty_name="DeepSeek V3.1",
        inference_provider="fireworks-ai",
        company_pretty_name="DeepSeek",
        open_weights=True,
        agent_type="codeagent",
    ),
]


@app.command()
def main(
    max_events: int = typer.Option(5, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7 * 6, help="Days until event ending"),
    weeks_back: int = typer.Option(
        7, help="Number of weeks to go back for backward mode"
    ),
):
    """Main script to run investment analysis with all models across past Sundays."""

    all_results = []

    logger.info("Starting investment analysis with all models across past Sundays")

    # Find the most recent Sunday
    today = date.today()
    days_since_sunday = today.weekday() + 1  # Monday is 0, Sunday is 6
    if days_since_sunday == 7:  # Today is Sunday
        days_since_sunday = 0
    most_recent_sunday = today - timedelta(days=days_since_sunday)
    
    # Generate dates for the past weeks' Sundays, starting with the oldest
    dates_to_process = []
    for week_offset in range(
        weeks_back, 0, -1
    ):  # Start from oldest to newest
        sunday_date = most_recent_sunday - timedelta(weeks=week_offset)
        dates_to_process.append(sunday_date)

    # Add the most recent Sunday
    dates_to_process.append(most_recent_sunday)

    # Run for each date and each model
    for target_date in dates_to_process:
        run_investments_for_specific_date(
            time_until_ending=timedelta(days=days_ahead),
            max_n_events=max_events,
            models=BACKWARD_MODE_MODELS,  # Run one model at a time
            target_date=target_date,
        )

    logger.info(f"All analyses completed. Total results: {len(all_results)}")


if __name__ == "__main__":
    app()
