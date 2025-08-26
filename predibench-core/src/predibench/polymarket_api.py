from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

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

from predibench.common import BASE_URL_POLYMARKET
from predibench.logger_config import get_logger
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
            self.prices = ts_request.get_token_daily_timeseries()
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

        for market in markets:
            market.fill_prices(end_datetime)
        return markets


class _HistoricalTimeSeriesRequestParameters(BaseModel):
    clob_token_id: str
    end_datetime: datetime | None = None

    @polymarket_retry
    def get_token_daily_timeseries(self) -> pd.Series | None:
        """Make a single API request for timeseries data."""
        url = "https://clob.polymarket.com/prices-history"
        assert self.clob_token_id is not None

        set_of_params = [
            {
                "market": self.clob_token_id,
                "interval": "max",
                "fidelity": "1440",
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
                    [datetime.fromtimestamp(point["t"]) for point in data["history"]]
                ),
            )
            .sort_index()
            .resample("1D")
            .last()
            .ffill()
        )
        timeseries.index = timeseries.index.tz_localize(timezone.utc).date

        # Filter timeseries to only include dates between start_datetime and end_datetime
        if self.end_datetime is not None:
            timeseries = timeseries.loc[timeseries.index <= self.end_datetime.date()]

        # assert len(timeseries) > 0, (
        #     f"No timeseries data found for market {self.clob_token_id}"
        # )

        return timeseries


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


################################################################################
# Useful for the future but unused functions
################################################################################


class OrderLevel(BaseModel):
    price: str
    size: str


class OrderBook(BaseModel):
    market: str
    asset_id: str
    hash: str
    timestamp: str
    min_order_size: str
    neg_risk: bool
    tick_size: str
    bids: list[OrderLevel]
    asks: list[OrderLevel]

    @staticmethod
    @polymarket_retry
    def get_order_book(token_id: str) -> OrderBook:
        """Get order book for a specific token ID from Polymarket CLOB API.

        Args:
            token_id: Token ID of the market to get the book for

        Returns:
            OrderBook containing bids, asks, and market information
        """
        url = "https://clob.polymarket.com/book"
        params = {"token_id": token_id}

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        bids = [
            OrderLevel(price=bid["price"], size=bid["size"]) for bid in data["bids"]
        ]
        asks = [
            OrderLevel(price=ask["price"], size=ask["size"]) for ask in data["asks"]
        ]

        return OrderBook(
            market=data["market"],
            asset_id=data["asset_id"],
            hash=data["hash"],
            timestamp=data["timestamp"],
            min_order_size=data["min_order_size"],
            neg_risk=data["neg_risk"],
            tick_size=data["tick_size"],
            bids=bids,
            asks=asks,
        )
