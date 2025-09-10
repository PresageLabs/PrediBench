from datetime import datetime
from predibench.logger_config import get_logger
from functools import cache

logger = get_logger(__name__)


def date_to_string(date: datetime) -> str:
    """Convert a datetime object to YYYY-MM-DD string format."""
    return date.strftime("%Y-%m-%d")


def string_to_date(date_str: str) -> datetime:
    """Convert a YYYY-MM-DD string to datetime object."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def convert_polymarket_time_to_datetime(time_str: str) -> datetime:
    """Convert a Polymarket time string to a datetime object."""
    return datetime.fromisoformat(time_str.replace("Z", "")).replace(tzinfo=None)

