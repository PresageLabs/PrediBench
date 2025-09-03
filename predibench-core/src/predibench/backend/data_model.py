from pydantic import BaseModel
from typing import Optional, Dict, List, Literal
import pandas as pd


class DataPointBackend(BaseModel):
    date: str
    value: float


class PricePointBackend(BaseModel):
    date: str
    price: float


class PositionPointBackend(BaseModel):
    date: str
    position: float


class PnlPointBackend(BaseModel):
    date: str
    pnl: float


class LeaderboardEntryBackend(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    lastUpdated: str
    trend: Literal['up', 'down', 'stable']
    pnl_history: List[DataPointBackend]
    avg_brier_score: float


class MarketOutcomeBackend(BaseModel):
    clob_token_id: str
    name: str
    price: float


class MarketBackend(BaseModel):
    id: str
    question: str
    slug: str
    description: str
    outcomes: List[MarketOutcomeBackend]


class EventBackend(BaseModel):
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
    markets: List[MarketBackend]


class MarketData(BaseModel):
    market_id: str
    question: str
    prices: List[PricePointBackend]
    positions: List[PositionPointBackend]
    pnl_data: List[PnlPointBackend]


# ModelMarketDetails is just a type alias for a dictionary
# This represents: { [marketId: string]: MarketData }
ModelMarketDetails = Dict[str, MarketData]


class StatsBackend(BaseModel):
    topFinalCumulativePnl: float
    avgPnl: float
    totalTrades: int
    totalProfit: float


class MarketInvestmentDecisionBackend(BaseModel):
    """Investment decision data for a specific market - matches frontend interface"""
    market_id: str
    model_name: str
    model_id: str
    bet: float
    odds: float
    confidence: float
    rationale: str
    date: str


class BackendData(BaseModel):
    """Comprehensive pre-computed data for all backend routes"""
    # Core data - matches API endpoints exactly
    leaderboard: List[LeaderboardEntryBackend]
    events: List[EventBackend]
    stats: StatsBackend
    
    # Model-specific data: model_id -> LeaderboardEntry
    model_details: Dict[str, LeaderboardEntryBackend]
    
    # Model investment data: model_id -> market data dict
    model_investment_details: Dict[str, ModelMarketDetails]
    
    # Event-specific data: event_id -> event details
    event_details: Dict[str, EventBackend]
    
    # Event market prices: event_id -> market_id -> price data points
    event_market_prices: Dict[str, Dict[str, List[PricePointBackend]]]
    
    # Event investment decisions: event_id -> list of decisions
    event_investment_decisions: Dict[str, List[MarketInvestmentDecisionBackend]]


# Typed results for PnL calculations
class PnlResultBackend(BaseModel):
    """Clean, typed result from PnL calculation"""
    cumulative_pnl: List[DataPointBackend]  # Time series for frontend charts
    final_pnl: float                 # Final cumulative value
    market_pnls: Dict[str, List[PnlPointBackend]]  # Per-market cumulative PnL over time
    
    class Config:
        arbitrary_types_allowed = True


class AgentPerformance(BaseModel):
    """Complete performance metrics for a single agent/model"""
    model_name: str
    final_cumulative_pnl: float
    pnl_history: List[DataPointBackend]
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