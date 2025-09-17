from predibench.strategies.portfolio import Strategy
from predibench.polymarket_api import Event
from datetime import datetime, date
from predibench.strategies.portfolio import Portfolio
from predibench.common import get_date_output_path
from predibench.storage_utils import file_exists_in_storage
from predibench.utils import string_to_date
from predibench.logger_config import get_logger
from predibench.polymarket_data import load_events_from_file
from predibench.agent.smolagents_utils import 

logger = get_logger(__name__)
class BasicStrategyMainVolume(Strategy):
    def perform_investment_strategy(self, decision_datetime: datetime, events: list[Event], *args, **kwargs) -> Portfolio:
        for event in events: 
            for market in event.markets:
                volume = market.volume24hr
        pass
    
    def callback_before_investment(self, *args, **kwargs) -> None:
        pass
    
    def callback_after_investment(self, *args, **kwargs) -> None:
        pass
    
def run_basic_strategy_main_volume():
    dates_to_run = ["2025-08-29", "2025-09-01","2025-09-03","2025-09-05","2025-09-08","2025-09-10","2025-09-12","2025-09-15","2025-09-17"]
    for date_to_run in dates_to_run:
        date_to_run = string_to_date(date_to_run)
        cache_file_path = get_date_output_path(date_to_run)
        cache_file_path = cache_file_path / "events.json"

        logger.info(f"Loading events from cache: {cache_file_path}")
        events = load_events_from_file(cache_file_path)
        strategy = BasicStrategyMainVolume(Portfolio(open_positions=[], unallocated_cash=1.0))
        strategy.run(decision_datetime=date_to_run, events=events)
    
if __name__ == "__main__":
    run_basic_strategy_main_volume()