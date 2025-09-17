from predibench.polymarket_api import Event
from predibench.agent.models import ModelInvestmentDecisions
from predibench.logger_config import get_logger
from predibench.storage_utils import file_exists_in_storage, read_from_storage
from predibench.agent.models import EventInvestmentDecisions
from pydantic import ValidationError
from datetime import date, datetime
from predibench.agent.models import ModelInfo
from pydantic import BaseModel
from typing import Any
from abc import ABC, abstractmethod

class InvestmentDecision(BaseModel):
    decision_datetime: datetime
    event_investment_decisions: list[EventInvestmentDecisions]
    
    
class Position(BaseModel):
    event_id: str
    market_id: str
    outcome: str
    shares: float # Should be an int but we keep it float for now to be able to test our current strategies
    purchase_price: float
    decision_datetime: datetime
    sell_price: float | None = None
    
class Portfolio(BaseModel):
    open_positions: list[Position] | None = None
    unallocated_cash: float


class Strategy(ABC):
    def __init__(self, portfolio: Portfolio) -> None:
        self.history_portfolios = [portfolio]
        
    @property
    def current_portfolio(self) -> Portfolio:
        return self.history_portfolios[-1]
        
    
    @abstractmethod
    def perform_investment_strategy(self, decision_datetime: datetime, events: list[Event], *args, **kwargs) -> Portfolio:
        return Portfolio(open_positions=[], unallocated_cash=0.0)
    
    @abstractmethod
    def callback_before_investment(self, *args, **kwargs) -> None:
        """callback before investment, can be used to add cash to the portfolio"""
        pass
    
    @abstractmethod
    def callback_after_investment(self, *args, **kwargs) -> None:
        """callback after investment, can be used to add fees after the transaction"""
        pass
    
        
    def add_cash_to_portfolio(self, amount: float) -> None:
        self.current_portfolio.unallocated_cash += amount
        
    def _assert_new_portfolio_is_valid(self, portfolio: Portfolio) -> None:
        """assert money is added or lost from the portfolio"""
        pass
    
    def _save_portfolio_to_history(self, portfolio: Portfolio) -> None:
        self.history_portfolios.append(portfolio)
    
    def run(self, decision_datetime: datetime, events: list[Event], *args, **kwargs) -> None:
        self.callback_before_investment(*args, **kwargs)
        self.current_portfolio = self.perform_investment_strategy(decision_datetime, events, *args, **kwargs)
        self._assert_new_portfolio_is_valid(self.current_portfolio)
        self.callback_after_investment(*args, **kwargs)
        self._save_portfolio_to_history(self.current_portfolio)
    
    

