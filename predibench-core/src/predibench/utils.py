from datetime import datetime
from predibench.logger_config import get_logger
from functools import cache

logger = get_logger(__name__)


def convert_polymarket_time_to_datetime(time_str: str) -> datetime:
    """Convert a Polymarket time string to a datetime object."""
    return datetime.fromisoformat(time_str.replace("Z", "")).replace(tzinfo=None)


@cache
def get_timestamp_string() -> str:
    """Generate a YY_MM_DD date string for filenames."""
    return datetime.now().strftime("%y_%m_%d")
