from pydantic import BaseModel
from typing import Optional, Dict, List, Literal
import pandas as pd


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


# Typed results for PnL calculations
class PnlResult(BaseModel):
    """Clean, typed result from PnL calculation"""
    cumulative_pnl: List[DataPoint]  # Time series for frontend charts
    final_pnl: float                 # Final cumulative value
    market_pnls: Dict[str, List[PnlPoint]]  # Per-market cumulative PnL over time
    
    class Config:
        arbitrary_types_allowed = True


class AgentPerformance(BaseModel):
    """Complete performance metrics for a single agent/model"""
    model_name: str
    final_cumulative_pnl: float
    pnl_history: List[DataPoint]
    avg_brier_score: float
    trades: int


class BrierResult(BaseModel):
    """Clean, typed result from Brier score calculation"""
    # DataFrame of per-date Brier scores per market (nullable when no decisions)
    brier_scores: pd.DataFrame
    # Average Brier score across all available predictions
    avg_brier_score: float
    
    class Config:
        arbitrary_types_allowed = True