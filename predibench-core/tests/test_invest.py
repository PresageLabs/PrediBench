from datetime import date, timedelta

from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from smolagents.models import InferenceClientModel


def test_invest():
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]
    target_date = date(2025, 7, 16)

    result = run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        target_date=target_date,
    )

    assert isinstance(result, list)
    if len(result) > 0:
        assert hasattr(result[0], "model_id")
        assert hasattr(result[0], "target_date")



if __name__ == "__main__":
    test_invest()
