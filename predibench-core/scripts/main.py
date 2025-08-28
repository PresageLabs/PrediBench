from datetime import date, timedelta

import typer
from predibench.agent.dataclasses import ModelInfo
from predibench.invest import run_investments_for_specific_date
from predibench.logger_config import get_logger

logger = get_logger(__name__)

app = typer.Typer()


MODEL_MAP = [
    ModelInfo(
        model_id="grok-4-0709",
        model_pretty_name="Grok 4",
        inference_provider="xai",
        company_pretty_name="xAI",
        agent_type="code",
    ),
    ModelInfo(
        model_id="gpt-5",
        model_pretty_name="GPT-5",
        inference_provider="openai",
        company_pretty_name="OpenAI",
    ),
    ModelInfo(
        model_id="gpt-5-mini",
        model_pretty_name="GPT-5 Mini",
        inference_provider="openai",
        company_pretty_name="OpenAI",
    ),
    ModelInfo(
        model_id="gpt-4.1",
        model_pretty_name="GPT-4.1",
        inference_provider="openai",
        company_pretty_name="OpenAI",
    ),
    ModelInfo(
        model_id="gpt-4.1-mini",
        model_pretty_name="GPT-4.1 Mini",
        inference_provider="openai",
        company_pretty_name="OpenAI",
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
        model_id="openai/gpt-oss-20b",
        model_pretty_name="GPT-OSS 20B",
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
        agent_type="code",
    ),
    ModelInfo(
        model_id="deepseek-ai/DeepSeek-R1",
        model_pretty_name="DeepSeek R1",
        inference_provider="fireworks-ai",
        company_pretty_name="DeepSeek",
        open_weights=True,
        agent_type="code",
    ),
    ModelInfo(
        model_id="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        model_pretty_name="Qwen3-Coder-480B-A35B-Instruct",
        inference_provider="fireworks-ai",
        company_pretty_name="Qwen",
        open_weights=True,
        agent_type="code",
    ),
    ModelInfo(
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        model_pretty_name="Llama 4 Maverick",
        inference_provider="fireworks-ai",
        company_pretty_name="Meta",
        open_weights=True,
    ),
    ModelInfo(
        model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        model_pretty_name="Llama 4 Scout",
        inference_provider="fireworks-ai",
        company_pretty_name="Meta",
        open_weights=True,
    ),
    ModelInfo(
        model_id="gemini-2.5-flash",
        model_pretty_name="Gemini 2.5 Flash",
        inference_provider="google",
        company_pretty_name="Google",
        agent_type="code",
    ),
    ModelInfo(
        model_id="gemini-2.5-pro",
        model_pretty_name="Gemini 2.5 Pro",
        inference_provider="google",
        company_pretty_name="Google",
        agent_type="code",
    ),
    ModelInfo(
        model_id="sonar-deep-research",
        model_pretty_name="Sonar Deep Research",
        inference_provider="perplexity",
        company_pretty_name="Perplexity",
    ),
    ModelInfo(
        model_id="o3-deep-research",
        model_pretty_name="O3 Deep Research",
        inference_provider="openai",
        company_pretty_name="OpenAI",
    ),
    # NOTE: add Claude, Grok
    ModelInfo(
        model_id="claude-sonnet-4-20250514",
        model_pretty_name="Claude Sonnet 4",
        inference_provider="anthropic",
        company_pretty_name="Anthropic",
    ),
    ModelInfo(
        model_id="claude-opus-4-1-20250805",
        model_pretty_name="Claude Opus 4.1",
        inference_provider="anthropic",
        company_pretty_name="Anthropic",
    ),
]


@app.command()
def main(
    model_name: str = typer.Argument("all", help="Name of the model to run"),
    max_events: int = typer.Option(10, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7 * 6, help="Days until event ending"),
):
    """Main script to run investment analysis with a single model."""

    if model_name == "all":
        models = MODEL_MAP
    elif model_name == "open_models":
        models = [model for model in MODEL_MAP if model.open_weights]
    elif model_name == "openai":
        models = [model for model in MODEL_MAP if model.inference_provider == "openai"]
    elif model_name in [model.model_id for model in MODEL_MAP]:
        models = [model for model in MODEL_MAP if model.model_id == model_name]
    else:
        available_models = ", ".join(
            [model.model_id for model in MODEL_MAP] + ["all", "open_models", "openai"]
        )
        typer.echo(
            f"Error: Model '{model_name}' not found. Available models: {available_models}"
        )
        raise typer.Exit(1)

    logger.info(f"Starting investment analysis with model: {model_name}")

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
