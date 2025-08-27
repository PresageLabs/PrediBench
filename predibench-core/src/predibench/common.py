from pathlib import Path
from datetime import date


PREDIBENCH_PATH = Path(__file__).parent
PREDIBENCH_REPO_PATH = PREDIBENCH_PATH.parent.parent.parent

DATA_PATH = PREDIBENCH_REPO_PATH / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

BASE_URL_POLYMARKET = "https://gamma-api.polymarket.com"

def get_date_output_path(target_date: date) -> Path:
    """
    Get the path to the date output for a given target date.
    """
    date_output_path = DATA_PATH / target_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)
    return date_output_path
