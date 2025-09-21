import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ciso8601
import pandas as pd
import requests
from predibench.backend.data_loader import (
    file_exists_in_storage,
    read_from_storage,
)
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger
from predibench.storage_utils import write_to_storage
from pydantic import BaseModel
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = get_logger(__name__)

polymarket_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    retry=retry_if_exception_type(
        (
            requests.exceptions.RequestException,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        )
    ),
    before_sleep=before_sleep_log(logger, log_level=logging.WARNING),
    after=after_log(logger, log_level=logging.INFO),
    reraise=True,
)


class _HistoricalTimeSeriesRequest(BaseModel):
    clob_token_id: str
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    cache_results: bool = True
    resample: str | timedelta | None = "1D"
    fidelity: int | None = None
    url: str | None = None
    update_cache: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.clob_token_id is not None
        self.url = "https://clob.polymarket.com/prices-history"

    @polymarket_retry
    def get_token_daily_timeseries(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        fidelity: int | None = None,
        resample: str | timedelta | None = None,
    ) -> pd.Series:
        """Make a single API request for timeseries data."""
        effective_start_datetime = start_datetime or self.start_datetime
        effective_end_datetime = end_datetime or self.end_datetime
        effective_fidelity = fidelity or self.fidelity
        effective_resample = resample or self.resample
        assert (
            effective_start_datetime is not None and effective_end_datetime is not None
        ), "Need to specify start and end datetime"

        # Normalize to timezone-aware UTC
        effective_start_datetime = effective_start_datetime.astimezone(timezone.utc)
        effective_end_datetime = effective_end_datetime.astimezone(timezone.utc)

        # If too long, split into several
        if effective_end_datetime - effective_start_datetime > timedelta(
            days=14, hours=23, minutes=0
        ):
            start_datetimes = [
                dt.to_pydatetime()
                for dt in pd.date_range(
                    start=effective_start_datetime,
                    end=effective_end_datetime,
                    freq=timedelta(days=14, hours=23, minutes=0),
                )
            ]
            end_datetimes = start_datetimes[1:] + [effective_end_datetime]
            all_timeseries = []
            for sub_start_datetime, sub_end_datetime in zip(
                start_datetimes, end_datetimes
            ):
                new_timeseries = self.get_token_daily_timeseries(
                    start_datetime=sub_start_datetime,
                    end_datetime=sub_end_datetime,
                    fidelity=effective_fidelity,
                    resample=effective_resample,
                )
                if len(new_timeseries) > 0:
                    all_timeseries.append(new_timeseries)
            timeseries = pd.concat(all_timeseries) if all_timeseries else pd.Series()

        else:
            start_ts = int(effective_start_datetime.timestamp())
            end_ts = int(effective_end_datetime.timestamp())
            set_of_params = [
                {
                    "market": self.clob_token_id,
                    "startTs": start_ts,
                    "endTs": end_ts,
                    "fidelity": str(effective_fidelity)
                    if effective_fidelity is not None
                    else None,
                },
                {
                    "market": self.clob_token_id,
                    "startTs": start_ts,
                    "endTs": end_ts,
                },
            ]
            for params in set_of_params:
                # Remove None values
                clean_params = {k: v for k, v in params.items() if v is not None}
                response = requests.get(self.url, params=clean_params)
                response.raise_for_status()
                data = response.json()
                if len(data["history"]) > 0:
                    break

            timeseries = pd.Series(
                [point["p"] for point in data["history"]],
                index=pd.to_datetime(
                    [
                        datetime.fromtimestamp(point["t"], tz=timezone.utc)
                        for point in data["history"]
                    ],
                    utc=True,
                ),
            ).sort_index()

        if effective_resample:
            timeseries = timeseries.resample(effective_resample).last()
        timeseries = timeseries.ffill()
        return timeseries

    def get_cached_token_timeseries(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        fidelity: int | None = None,
        resample: str | timedelta | None = None,
    ) -> pd.Series | None:
        """Get token timeseries from cache if available, otherwise fetch from API."""
        cache_path = self._get_cache_path()

        if file_exists_in_storage(cache_path) and self.cache_results:
            try:
                t = time.time()
                cached_data = json.loads(read_from_storage(cache_path))
                cached_timeseries = self._deserialize_timeseries(cached_data)

                # Check if cached data covers the required date range
                if not self.update_cache:
                    logger.debug(
                        f"Using cached timeseries for token {self.clob_token_id[:10]}[...] : loaded {len(cached_timeseries)} points in {time.time() - t:.2f} seconds"
                    )
                    return cached_timeseries
                else:
                    logger.debug(
                        f"Cache for {self.clob_token_id} is outdated, updating..."
                    )
                    return self.update_cached_token_timeseries()

            except json.JSONDecodeError as e:
                raise e
                logger.warning(
                    f"Failed to load cached data for {self.clob_token_id}: {e}"
                )

        # If no cache or cache loading failed, fetch fresh data
        return self._fetch_and_cache_timeseries(
            start_datetime, end_datetime, fidelity, resample
        )

    def update_cached_token_timeseries(
        self, force_update: bool = False
    ) -> pd.Series | None:
        """Update cached timeseries data with new information."""
        cache_path = self._get_cache_path()
        existing_data = None

        # Check if market is already marked as closed in cache
        if file_exists_in_storage(cache_path):
            try:
                cached_data: dict = json.loads(read_from_storage(cache_path))
                if cached_data.get("is_closed", False) and not force_update:
                    logger.info(
                        f"Skipping update for closed market {self.clob_token_id}"
                    )
                    return self._deserialize_timeseries(cached_data)
                existing_data = self._deserialize_timeseries(cached_data)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to load existing cached data for {self.clob_token_id}: {e}"
                )

        # Fetch fresh data
        merged_fresh_data = self._combine_timeseries()

        if merged_fresh_data is None:
            return None

        # Check if market should be marked as closed (last price > 2 days old)
        is_closed = self._check_if_market_closed(merged_fresh_data)

        # Merge with existing data if available
        if existing_data is not None:
            final_data = self._merge_timeseries(existing_data, merged_fresh_data)
        else:
            final_data = merged_fresh_data

        # Cache the final data with closed status
        if final_data is not None:
            serialized_data = self._serialize_timeseries(
                final_data, is_closed=is_closed
            )
            write_to_storage(cache_path, json.dumps(serialized_data, indent=2))
            logger.info(
                f"Cached timeseries data for token {self.clob_token_id} (closed: {is_closed})"
            )

        return final_data

    def _get_cache_path(self) -> Path:
        """Get the cache file path for this token."""
        return DATA_PATH / "timeseries_cache" / f"{self.clob_token_id}.json"

    def _combine_timeseries(self) -> pd.Series | None:
        """Fetch fresh timeseries data from API with both 24h and 6h fidelity."""
        # Try with 24h fidelity first, then 6h fidelity
        timeseries_24h = self.get_token_daily_timeseries(fidelity=60 * 24)
        timeseries_6h = self.get_token_daily_timeseries(fidelity=60 * 6, resample="6h")

        # Merge the data
        return self._merge_timeseries(timeseries_24h, timeseries_6h)

    def _fetch_and_cache_timeseries(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        fidelity: int | None = None,
        resample: str | timedelta | None = None,
    ) -> pd.Series | None:
        """Fetch timeseries data from API and cache it."""
        if fidelity or self.fidelity:
            data = self.get_token_daily_timeseries(
                fidelity=self.fidelity or fidelity,
                resample=self.resample or resample,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )
        else:
            data = self._combine_timeseries()

        if data is not None and self.cache_results:
            cache_path = self._get_cache_path()
            serialized_data = self._serialize_timeseries(
                data, is_closed=self._check_if_market_closed(data)
            )
            print("Writinc to cache under :", cache_path)
            write_to_storage(cache_path, json.dumps(serialized_data, indent=2))
            logger.info(f"Cached timeseries data for token {self.clob_token_id}")

        return data

    def _merge_timeseries(
        self, ts1: pd.Series | None, ts2: pd.Series | None
    ) -> pd.Series | None:
        """Merge two timeseries, preferring newer data and filling gaps."""
        if ts1 is None and ts2 is None:
            return None
        if ts1 is None:
            return ts2
        if ts2 is None:
            return ts1

        # Combine the series and remove duplicates, keeping the last (most recent) value
        combined = pd.concat([ts1, ts2]).groupby(level=0).last()
        return combined.sort_index()

    def _serialize_timeseries(self, ts: pd.Series, is_closed: bool = False) -> dict:
        """Convert pandas Series to JSON-serializable format."""
        return {
            "data": [
                {"datetime": timestamp.isoformat(), "value": float(value)}
                for timestamp, value in ts.items()
            ],
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "is_closed": is_closed,
        }

    def _deserialize_timeseries(self, data: dict) -> pd.Series:
        """Convert JSON data back to pandas Series."""
        dt = [ciso8601.parse_datetime(x["datetime"]) for x in data["data"]]

        # Build a DatetimeIndex
        idx = pd.DatetimeIndex(dt)

        # Ensure UTC (if already tz-aware, convert; if not, localize)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")

        # Values as float32 for compactness
        return pd.Series([x["value"] for x in data["data"]], index=idx).sort_index()

    def _is_cache_up_to_date(
        self, cached_timeseries: pd.Series, cached_data: dict | None = None
    ) -> bool:
        """Check if cached timeseries covers the required date range or if market is closed."""
        if cached_timeseries is None or len(cached_timeseries) == 0:
            return False

        # Check if market is closed - if so, cache is always up to date
        if cached_data and cached_data.get("is_closed", False):
            return True

        # Get the latest cached timestamp
        max_cached_timestamp = cached_timeseries.index.max()

        # Ensure cached timestamp has timezone info
        if (
            hasattr(max_cached_timestamp, "tzinfo")
            and max_cached_timestamp.tzinfo is None
        ):
            max_cached_timestamp = max_cached_timestamp.replace(tzinfo=timezone.utc)

        # Get today's date in UTC
        today_utc = datetime.now(timezone.utc).date()

        # Check if the latest value is from the same day as today (in UTC)
        max_cached_date = max_cached_timestamp.date()
        if max_cached_date == today_utc:
            return True

        # If we have an end_datetime specified, check if it's covered by the cached data
        if self.end_datetime is not None:
            target_datetime = self.end_datetime
            # Ensure target_datetime has timezone info
            if target_datetime.tzinfo is None:
                target_datetime = target_datetime.replace(tzinfo=timezone.utc)

            # Check if the target datetime is covered by the cached data
            return target_datetime <= max_cached_timestamp

        # If no end_datetime specified and latest data is not from today, cache is outdated
        return False

    def _check_if_market_closed(self, timeseries: pd.Series) -> bool:
        """Check if market is closed based on last price."""
        if timeseries is None or len(timeseries) == 0:
            return True

        # Get the most recent timestamp
        last_timestamp = timeseries.index.max()

        # Ensure timezone awareness
        if hasattr(last_timestamp, "tzinfo") and last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)

        # Check if last price is older than 12 hours
        two_days_ago = datetime.now(timezone.utc) - timedelta(hours=12)
        return last_timestamp < two_days_ago
