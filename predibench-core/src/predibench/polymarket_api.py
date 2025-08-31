from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

# TODO: respect rate limits:
# **API Rate Limits**
# Endpoint	Limit	Notes
# /books (website)	300 requests / 10s	Throttle requests over the maximum configured rate
# /books	50 requests / 10s	Throttle requests over the maximum configured rate
# /price	100 requests / 10s	Throttle requests over the maximum configured rate
# markets/0x	50 requests / 10s	Throttle requests over the maximum configured rate
# POST /order	500 requests / 10s (50/s)	Burst; throttle requests over the maximum configured rate
# POST /order	3000 requests / 10 min (5/s)	Throttle requests over the maximum configured rate
# DELETE /order	500 requests / 10s (50/s)	Burst; throttle requests over the maximum configured rate
# DELETE /order	3000 requests / 10 min (5/s)	Throttle requests over the maximum configured rate
from pydantic import BaseModel
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from predibench.common import BASE_URL_POLYMARKET, DATA_PATH
from predibench.logger_config import get_logger
from predibench.storage_utils import (
    file_exists_in_storage,
    read_from_storage,
    write_to_storage,
)
from predibench.utils import convert_polymarket_time_to_datetime

MAX_INTERVAL_TIMESERIES = timedelta(days=14, hours=23, minutes=0)
# NOTE: above is refined by experience: seems independant from the resolution

logger = get_logger(__name__)

# Common retry configuration for all API calls
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


class MarketOutcome(BaseModel):
    clob_token_id: str
    name: str
    price: float


class Market(BaseModel, arbitrary_types_allowed=True):
    id: str
    question: str
    slug: str
    description: str
    end_datetime: datetime | None
    creation_datetime: datetime
    volumeNum: float | None
    volume24hr: float | None
    volume1wk: float | None
    volume1mo: float | None
    volume1yr: float | None
    liquidity: float | None
    outcomes: list[MarketOutcome]
    prices: pd.Series | None = None
    price_outcome_name: str | None = None  # Name of the outcome the prices represent

    def fill_prices(self, end_datetime: datetime | None = None) -> None:
        """Fill the prices field with timeseries data.

        Args:
            start_datetime: Start time for timeseries data
            end_datetime: End time for timeseries data
            interval: Time interval for data points (default: "1d")
        """
        if self.outcomes and len(self.outcomes) == 2 and self.outcomes[0].clob_token_id:
            ts_request = _HistoricalTimeSeriesRequestParameters(
                clob_token_id=self.outcomes[0].clob_token_id,
                end_datetime=end_datetime,
            )
            self.prices = ts_request.get_cached_token_timeseries()
            self.price_outcome_name = self.outcomes[
                0
            ].name  # Store which outcome the prices represent
            assert self.price_outcome_name.lower() != "no", (
                "Price outcome should be YES or a sport's team name."
            )
        else:
            logger.error(
                f"Incorrect outcomes for market {self.id} with name {self.question} and outcomes {self.outcomes}"
            )
            self.prices = None
            self.price_outcome_name = None

    @staticmethod
    def _convert_to_daily_data(timeseries_data: pd.Series) -> pd.Series:
        """Convert 6-hourly datetime data to daily date data for PnL compatibility."""
        if timeseries_data is None or len(timeseries_data) == 0:
            return timeseries_data
        
        # Resample to daily data (taking the last value of each day)
        daily_data = timeseries_data.resample('1D').last().dropna()
        
        # Convert datetime index to date index for PnL compatibility
        daily_data.index = daily_data.index.date
        
        return daily_data

    @staticmethod
    def from_json(market_data: dict) -> Market:
        """Convert a market JSON object to a PolymarketMarket dataclass."""

        assert "outcomes" in market_data
        outcomes = json.loads(market_data["outcomes"])
        assert len(outcomes) >= 2, (
            f"Expected at least 2 outcomes, got {len(outcomes)} for market:\n{market_data['id']}\n{market_data['question']}"
        )
        outcome_names = json.loads(market_data["outcomes"])

        # Handle missing price data
        if "outcomePrices" in market_data:
            outcome_prices = json.loads(market_data["outcomePrices"])
        else:
            # Default to 0.5 for all outcomes if prices not available
            outcome_prices = [0.5] * len(outcomes)

        # Handle missing token IDs
        if "clobTokenIds" in market_data:
            outcome_clob_token_ids = json.loads(market_data["clobTokenIds"])
        else:
            # Use empty strings if token IDs not available
            outcome_clob_token_ids = [""] * len(outcomes)
        return Market(
            id=market_data["id"],
            question=market_data["question"],
            outcomes=[
                MarketOutcome(
                    clob_token_id=outcome_clob_token_ids[i],
                    name=outcome_names[i],
                    price=outcome_prices[i],
                )
                for i in range(len(outcomes))
            ],
            slug=market_data["slug"],
            description=market_data["description"],
            end_datetime=convert_polymarket_time_to_datetime(market_data["endDate"])
            if "endDate" in market_data
            else None,
            creation_datetime=convert_polymarket_time_to_datetime(
                market_data["createdAt"]
            ),
            volumeNum=float(market_data["volumeNum"])
            if market_data.get("volumeNum") is not None
            else None,
            volume24hr=float(market_data["volume24hr"])
            if market_data.get("volume24hr") is not None
            else None,
            volume1wk=float(market_data["volume1wk"])
            if market_data.get("volume1wk") is not None
            else None,
            volume1mo=float(market_data["volume1mo"])
            if market_data.get("volume1mo") is not None
            else None,
            volume1yr=float(market_data["volume1yr"])
            if market_data.get("volume1yr") is not None
            else None,
            liquidity=float(market_data["liquidity"])
            if "liquidity" in market_data and market_data["liquidity"] is not None
            else None,
            # json=market_data,
        )


class _RequestParameters(BaseModel):
    limit: int | None = None
    offset: int | None = None
    order: str | None = None
    ascending: bool | None = None
    id: int | None = None
    slug: str | None = None
    archived: bool | None = None
    active: bool | None = None
    closed: bool | None = None
    clob_token_ids: str | None = None
    condition_ids: str | None = None
    liquidity_num_min: float | None = None
    liquidity_num_max: float | None = None
    volume_num_min: float | None = None
    volume_num_max: float | None = None
    start_date_min: date | None = None
    start_date_max: date | None = None
    end_date_min: date | None = (
        None  # NOTE: In the API it must be a date, see https://docs.polymarket.com/developers/gamma-markets-api/get-events
    )
    end_date_max: date | None = None
    tag_id: int | None = None
    related_tags: bool | None = None


class MarketsRequestParameters(_RequestParameters):
    @polymarket_retry
    def get_markets(
        self,
        end_datetime: datetime | None = None,
        fill_prices: bool = True,
    ) -> list[Market]:
        """Get open markets from Polymarket API using this request configuration.

        Args:
            end_datetime: Limit datetime to fill market prices.
        """
        url = f"{BASE_URL_POLYMARKET}/markets"

        if self.limit and self.limit > 500:
            assert False, "Limit must be less than or equal to 500"

        params = {}
        for field_name, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, bool):
                    params[field_name] = "true" if value else "false"
                elif isinstance(value, datetime):
                    params[field_name] = value.date().isoformat()
                else:
                    params[field_name] = value

        response = requests.get(url, params=params)
        response.raise_for_status()
        output = response.json()
        markets = [Market.from_json(market) for market in output]
        if self.end_date_min and self.end_date_max:
            filtered_markets = []
            excluded_count = 0
            for market in markets:
                assert market is not None
                if market.end_datetime is not None and not (
                    self.end_date_min <= market.end_datetime.date() <= self.end_date_max
                ):
                    excluded_count += 1
                    logger.warning(
                        f"Excluded market {market.question} because it doesn't fit the date criteria"
                    )
                else:
                    filtered_markets.append(market)
            if excluded_count > 0:
                logger.warning(
                    f"Excluded {excluded_count} markets that don't fit the date criteria"
                )
            markets = filtered_markets

        if fill_prices:
            for market in markets:
                market.fill_prices(end_datetime)
        return markets


class _HistoricalTimeSeriesRequestParameters(BaseModel):
    clob_token_id: str
    end_datetime: datetime | None = None

    @polymarket_retry
    def get_token_daily_timeseries(self, fidelity: int = 60*24, interval: str = "max", resamble: str | timedelta = "1D") -> pd.Series[datetime, float] | None:
        """Make a single API request for timeseries data."""
        url = "https://clob.polymarket.com/prices-history"
        assert self.clob_token_id is not None

        set_of_params = [
            {
                "market": self.clob_token_id,
                "interval": interval,
                "fidelity": str(fidelity),
            },
            {
                "market": self.clob_token_id,
                "interval": "max",
            },
        ]
        for params in set_of_params:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if len(data["history"]) > 0:
                break

        timeseries = (
            pd.Series(
                [point["p"] for point in data["history"]],
                index=pd.to_datetime(
                    [datetime.fromtimestamp(point["t"], tz=timezone.utc) for point in data["history"]],utc=True
                ),
            )
            .sort_index()
            .resample(resamble)
            .last()
            .ffill()
        )

        if self.end_datetime is not None:
            # Ensure end_datetime has timezone info for comparison
            end_dt = self.end_datetime
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            timeseries = timeseries.loc[timeseries.index <= end_dt]

        return timeseries

    def get_cached_token_timeseries(self) -> pd.Series | None:
        """Get token timeseries from cache if available, otherwise fetch from API."""
        cache_path = self._get_cache_path()
        
        if file_exists_in_storage(cache_path):
            try:
                cached_data = json.loads(read_from_storage(cache_path))
                cached_timeseries = self._deserialize_timeseries(cached_data)
                
                # Check if cached data covers the required date range
                if self._is_cache_up_to_date(cached_data=cached_data, cached_timeseries=cached_timeseries):
                    return cached_timeseries
                else:
                    logger.info(f"Cache for {self.clob_token_id} is outdated, updating...")
                    return self.update_cached_token_timeseries()
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to load cached data for {self.clob_token_id}: {e}")
        
        # If no cache or cache loading failed, fetch fresh data
        return self._fetch_and_cache_timeseries()

    def update_cached_token_timeseries(self, force_update: bool = False) -> pd.Series | None:
        """Update cached timeseries data with new information."""
        cache_path = self._get_cache_path()
        existing_data = None
        
        # Check if market is already marked as closed in cache
        if file_exists_in_storage(cache_path):
            try:
                cached_data:dict = json.loads(read_from_storage(cache_path))
                if cached_data.get("is_closed", False) and not force_update:
                    logger.info(f"Skipping update for closed market {self.clob_token_id}")
                    return self._deserialize_timeseries(cached_data)
                existing_data = self._deserialize_timeseries(cached_data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to load existing cached data for {self.clob_token_id}: {e}")
        
        
        # Fetch fresh data
        merged_fresh_data = self._fetch_fresh_timeseries()
        
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
            serialized_data = self._serialize_timeseries(final_data, is_closed=is_closed)
            write_to_storage(cache_path, json.dumps(serialized_data, indent=2))
            logger.info(f"Cached timeseries data for token {self.clob_token_id} (closed: {is_closed})")
        
        return final_data

    def _get_cache_path(self) -> Path:
        """Get the cache file path for this token."""
        return DATA_PATH / "timeseries_cache" / f"{self.clob_token_id}.json"
    
    def _fetch_fresh_timeseries(self) -> pd.Series | None:
        """Fetch fresh timeseries data from API with both 24h and 6h fidelity."""
        # Try with 24h fidelity first, then 6h fidelity
        timeseries_24h = self.get_token_daily_timeseries(fidelity=60*24)
        timeseries_6h = self.get_token_daily_timeseries(fidelity=60*6, resamble="6H")
        
        # Merge the data
        return self._merge_timeseries(timeseries_24h, timeseries_6h)

    def _fetch_and_cache_timeseries(self) -> pd.Series | None:
        """Fetch timeseries data from API and cache it."""
        merged_data = self._fetch_fresh_timeseries()
        
        if merged_data is not None:
            # Check if market should be marked as closed
            is_closed = self._check_if_market_closed(merged_data)
            
            # Cache the merged data
            cache_path = self._get_cache_path()
            serialized_data = self._serialize_timeseries(merged_data, is_closed=is_closed)
            write_to_storage(cache_path, json.dumps(serialized_data, indent=2))
            logger.info(f"Cached timeseries data for token {self.clob_token_id} (closed: {is_closed})")
        
        return merged_data

    def _merge_timeseries(self, ts1: pd.Series | None, ts2: pd.Series | None) -> pd.Series | None:
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
            "data": [{"datetime": timestamp.isoformat(), "value": float(value)} for timestamp, value in ts.items()],
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "is_closed": is_closed
        }

    def _deserialize_timeseries(self, data: dict) -> pd.Series:
        """Convert JSON data back to pandas Series."""
        series_data = []
        timestamps = []
        
        for item in data["data"]:
            timestamp = pd.to_datetime(item["datetime"])
            # Ensure timezone info is UTC
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            timestamps.append(timestamp)
            series_data.append(item["value"])
        
        return pd.Series(series_data, index=timestamps)

    def _is_cache_up_to_date(self, cached_timeseries: pd.Series, cached_data: dict | None = None) -> bool:
        """Check if cached timeseries covers the required date range or if market is closed."""
        if cached_timeseries is None or len(cached_timeseries) == 0:
            return False
        
        # Check if market is closed - if so, cache is always up to date
        if cached_data and cached_data.get("is_closed", False):
            return True
        
        # Get the latest cached timestamp
        max_cached_timestamp = cached_timeseries.index.max()
        
        # Ensure cached timestamp has timezone info
        if hasattr(max_cached_timestamp, 'tzinfo') and max_cached_timestamp.tzinfo is None:
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
        if hasattr(last_timestamp, 'tzinfo') and last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        
        # Check if last price is older than 12 hours
        two_days_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        return last_timestamp < two_days_ago


class EventsRequestParameters(_RequestParameters):
    @polymarket_retry
    def get_events(self) -> list[Event]:
        """Get events from Polymarket API using this request configuration."""
        url = f"{BASE_URL_POLYMARKET}/events"

        if self.limit and self.limit > 500:
            assert False, "Limit must be less than or equal to 500"

        params = {}
        for field_name, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, bool):
                    params[field_name] = "true" if value else "false"
                elif isinstance(value, datetime):
                    params[field_name] = value.date().isoformat()
                else:
                    params[field_name] = value

        response = requests.get(url, params=params)
        response.raise_for_status()
        output = response.json()

        events = []
        for event_data in output:
            event = Event.from_json(event_data)
            events.append(event)

        return events


class Event(BaseModel, arbitrary_types_allowed=True):
    id: str
    slug: str
    title: str
    tags: list[str] | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    creation_datetime: datetime
    volume: float | None = None
    volume24hr: float | None = None
    volume1wk: float | None = None
    volume1mo: float | None = None
    volume1yr: float | None = None
    liquidity: float | None = None
    markets: list[Market]

    @staticmethod
    def from_json(event_data: dict) -> Event:
        """Convert an event JSON object to an Event dataclass."""
        markets = []
        for market_data in event_data.get("markets", []):
            market = Market.from_json(market_data)
            if market is not None:
                markets.append(market)

        return Event(
            id=event_data["id"],
            slug=event_data["slug"],
            title=event_data["title"],
            tags=[tag["label"] for tag in event_data["tags"]]
            if "tags" in event_data
            else None,
            description=event_data.get("description", None),
            start_datetime=convert_polymarket_time_to_datetime(event_data["startDate"])
            if "startDate" in event_data
            else None,
            end_datetime=convert_polymarket_time_to_datetime(event_data["endDate"])
            if "endDate" in event_data
            else None,
            creation_datetime=convert_polymarket_time_to_datetime(
                event_data["createdAt"]
            ),
            volume=float(event_data["volume"])
            if event_data.get("volume") is not None
            else None,
            volume24hr=float(event_data["volume24hr"])
            if event_data.get("volume24hr") is not None
            else None,
            volume1wk=float(event_data["volume1wk"])
            if event_data.get("volume1wk") is not None
            else None,
            volume1mo=float(event_data["volume1mo"])
            if event_data.get("volume1mo") is not None
            else None,
            volume1yr=float(event_data["volume1yr"])
            if event_data.get("volume1yr") is not None
            else None,
            liquidity=float(event_data["liquidity"])
            if event_data.get("liquidity") is not None
            else None,
            markets=markets,
        )

def load_market_price(clob_token_id: str) -> pd.Series | None:
    """Load market price from cache if available, otherwise fetch from API."""
    request_parameters = _HistoricalTimeSeriesRequestParameters(
        clob_token_id=clob_token_id,
    )
    return request_parameters.get_cached_token_timeseries()