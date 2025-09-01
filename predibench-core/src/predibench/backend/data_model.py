from pydantic import BaseModel
from typing import Optional, Dict, List, Literal


class DataPoint(BaseModel):
    date: str
    value: float


class PricePoint(BaseModel):
    date: str
    price: float


class PositionPoint(BaseModel):
    date: str
    position: float


class PnlPoint(BaseModel):
    date: str
    pnl: float


class LeaderboardEntry(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    lastUpdated: str
    trend: Literal['up', 'down', 'stable']
    pnl_history: List[DataPoint]
    avg_brier_score: float


class MarketOutcome(BaseModel):
    name: str
    price: float


class Market(BaseModel):
    id: str
    question: str
    slug: str
    description: str
    outcomes: List[MarketOutcome]


class Event(BaseModel):
    id: str
    slug: str
    title: str
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    creation_datetime: str
    volume: Optional[float] = None
    volume24hr: Optional[float] = None
    volume1wk: Optional[float] = None
    volume1mo: Optional[float] = None
    volume1yr: Optional[float] = None
    liquidity: Optional[float] = None
    markets: List[Market]


class MarketData(BaseModel):
    market_id: str
    question: str
    prices: List[PricePoint]
    positions: List[PositionPoint]
    pnl_data: List[PnlPoint]


# ModelMarketDetails is just a type alias for a dictionary
# This represents: { [marketId: string]: MarketData }
ModelMarketDetails = Dict[str, MarketData]


class Stats(BaseModel):
    topFinalCumulativePnl: float
    avgPnl: float
    totalTrades: int
    totalProfit: float