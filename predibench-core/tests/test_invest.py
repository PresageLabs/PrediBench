from datetime import date, timedelta

from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from predibench.models import ModelInfo


def test_invest():
    models = [
        ModelInfo(
            model_id="openai/gpt-oss-120b",
            model_pretty_name="GPT-OSS 120B",
            inference_provider="fireworks-ai",
            company_pretty_name="OpenAI",
            open_weights=True,
            agent_type="toolcalling",
        ),
    ]

    results = run_investments_for_specific_date(
        models=models,
        time_until_ending=timedelta(days=7 * 6),
        max_n_events=2,
        target_date=date(2025, 8, 24),
    )

def test_invest_without_cache():
    models = [
        ModelInfo(
            model_id="openai/gpt-oss-120b",
            model_pretty_name="GPT-OSS 120B",
            inference_provider="fireworks-ai",
            company_pretty_name="OpenAI",
            open_weights=True,
            agent_type="toolcalling",
        ),
    ]
    target_date = date(2025, 7, 16)

    result = run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=1,
        models=models,
        target_date=target_date,
        force_rewrite=True,
    )

    assert isinstance(result, list)
    if len(result) > 0:
        assert hasattr(result[0], "model_id")
        assert hasattr(result[0], "target_date")



if __name__ == "__main__":
    test_invest()
    test_invest_without_cache()
