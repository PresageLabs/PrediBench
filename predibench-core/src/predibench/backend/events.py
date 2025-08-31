from functools import lru_cache
from predibench.polymarket_api import Event, EventsRequestParameters
from predibench.backend.data_loader import load_agent_position



def get_events_that_received_predictions() -> list[Event]:
    """Get events based that models ran predictions on"""
    # Load agent choices to see what markets they've been betting on
    data = load_agent_position()

    # Working with Pydantic models from GCP
    event_ids = set()
    for model_result in data:
        for event_decision in model_result.event_investment_decisions:
            event_ids.add(event_decision.event_id)
    event_ids = tuple(event_ids)

    return get_events_by_ids(event_ids)



def get_events_by_ids(event_ids: tuple[str, ...]) -> list[Event]:
    """Cached wrapper for EventsRequestParameters.get_events()"""
    events = []
    for event_id in event_ids:
        events_request_parameters = EventsRequestParameters(
            id=event_id,
            limit=1,
        )
        events.append(events_request_parameters.get_events()[0])
    return events
