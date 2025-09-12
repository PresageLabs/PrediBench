from functools import lru_cache
from predibench.polymarket_api import Event, EventsRequestParameters
from predibench.agent.models import ModelInvestmentDecisions



def get_non_duplicated_events(events: list[Event]) -> list[Event]:
    """Remove duplicated events based on id and set market prices to latest available price"""
    # Remove duplicates based on event id
    unique_events = {}
    for event in events:
        if event.id not in unique_events:
            unique_events[event.id] = event
    
    # Convert to list and set latest market prices
    unique_events_list = list(unique_events.values())
    
    return unique_events_list

