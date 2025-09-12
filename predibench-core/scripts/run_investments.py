from datetime import date, timedelta

import typer
from predibench.common import DEFAULT_DAYS_AHEAD, DEFAULT_MAX_EVENTS
from predibench.invest import run_investments_for_specific_date
from predibench.logger_config import get_logger
from predibench.models import MODEL_MAP, MODELS_BY_PROVIDER
from predibench.retry_models import retry, stop_after_attempt

logger = get_logger(__name__)

app = typer.Typer()


@app.command()
@retry(
    stop=stop_after_attempt(2),
    reraise=False,
)
def main(
    provider: str = typer.Argument(
        "huggingface-qwen", help="Name of the provider to run models for"
    ),
    max_events: int = typer.Option(
        DEFAULT_MAX_EVENTS, help="Maximum number of events to analyze"
    ),
    days_ahead: int = typer.Option(DEFAULT_DAYS_AHEAD, help="Days until event ending"),
):
    """Main script to run investment analysis for models from a specific provider."""

    if provider == "all":
        models = MODEL_MAP
    elif provider == "events":
        models = []
    elif provider in MODELS_BY_PROVIDER:
        models = MODELS_BY_PROVIDER[provider]

    else:
        available_providers = ", ".join(list(MODELS_BY_PROVIDER.keys()) + ["all"])
        typer.echo(
            f"Error: Provider '{provider}' not found. Available providers and models: {available_providers}"
        )
        raise typer.Exit(1)

    logger.info(f"Starting investment analysis with provider: {provider}")

    results = run_investments_for_specific_date(
        models=models,
        target_date=date.today(),
        time_until_ending=timedelta(days=days_ahead),
        max_n_events=max_events,
        # output_path=DATA_PATH,
    )

    logger.info(f"Analysis completed. Results: {results}")


if __name__ == "__main__":
    app()
