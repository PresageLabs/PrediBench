from predibench.backend.data_loader import load_agent_position


def get_event_investment_decisions(event_id: str):
    """Get real investment choices for a specific event"""
    # Load agent choices data like in gradio app
    data = load_agent_position()

    # Working with Pydantic models from GCP
    market_investments = []

    # Get the latest prediction for each agent for this specific event ID
    agent_latest_predictions = {}
    for model_result in data:
        model_name = model_result.model_info.model_pretty_name
        for event_decision in model_result.event_investment_decisions:
            if event_decision.event_id == event_id:
                # Use target_date as a proxy for "latest" (assuming newer dates are more recent)
                if (
                    model_name not in agent_latest_predictions
                    or model_result.target_date
                    > agent_latest_predictions[model_name][0].target_date
                ):
                    agent_latest_predictions[model_name] = (
                        model_result,
                        event_decision,
                    )

    # Extract market decisions from latest predictions
    for model_result, event_decision in agent_latest_predictions.values():
        for market_decision in event_decision.market_investment_decisions:
            market_investments.append(
                {
                    "market_id": market_decision.market_id,
                    "model_name": model_result.model_info.model_pretty_name,
                    "model_id": model_result.model_id,
                    "bet": market_decision.model_decision.bet,
                    "odds": market_decision.model_decision.odds,
                    "confidence": market_decision.model_decision.confidence,
                    "rationale": market_decision.model_decision.rationale,
                    "date": model_result.target_date,
                }
            )

    return market_investments