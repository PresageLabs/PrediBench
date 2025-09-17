import time
from datetime import date, datetime

import numpy as np
from dotenv import load_dotenv
from predibench.agent.models import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInfo,
    ModelInvestmentDecisions,
    SingleInvestmentDecision,
)
from predibench.agent.smolagents_utils import (
    BET_DESCRIPTION,
    CompleteMarketInvestmentDecisions,
    run_openai_deep_research,
    run_perplexity_deep_research,
    run_smolagents,
)
from predibench.backend.data_model import FullModelResult
from predibench.date_utils import is_backward_mode
from predibench.logger_config import get_logger
from predibench.polymarket_api import Event, Market
from predibench.storage_utils import (
    file_exists_in_storage,
    read_from_storage,
    write_to_storage,
)
from predibench.utils import date_to_string
from pydantic import BaseModel, ValidationError
from smolagents import Timing

load_dotenv()

logger = get_logger(__name__)


class MarketInfo(BaseModel):
    id: str
    question: str
    description: str
    recent_prices: str
    current_price: float | None
    is_closed: bool
    outcomes: list[str]
    price_outcome_name: str


def _create_random_betting_decisions(
    market_data: dict[str, MarketInfo], model_info: ModelInfo
) -> CompleteMarketInvestmentDecisions:
    """Create random decisions for all markets with capital allocation constraint."""
    market_investments = []
    per_event_allocation = 1.0

    number_markets = len(market_data)
    invested_values = np.random.random(number_markets)
    invested_values = (
        per_event_allocation * invested_values / np.sum(invested_values)
    )  # Random numbers that sum to per_event_allocation

    for market_info, invested_value in zip(market_data.values(), invested_values):
        amount = invested_value

        model_decision = SingleInvestmentDecision(
            rationale=f"Random decision for testing market {market_info.id}",
            estimated_probability=np.random.uniform(0.1, 0.9),
            bet=amount,
            confidence=np.random.choice(list(range(1, 10))),
        )
        market_decision = MarketInvestmentDecision(
            market_id=market_info.id,
            decision=model_decision,
        )
        market_investments.append(market_decision)

    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=market_investments,
        unallocated_capital=0.0,
        token_usage=None,
        full_response={"model_type": "test_random"},
        sources_google=None,
        sources_visit_webpage=None,
    )


def _create_most_likely_outcome_decisions(
    market_data: dict[str, MarketInfo], model_info: ModelInfo
) -> CompleteMarketInvestmentDecisions:
    """Split amount equally between markets and invest based on price thresholds."""
    market_investments = []
    per_event_allocation = 1.0

    # Calculate amount per market
    nb_markets = len(market_data)
    amount_per_market = per_event_allocation / nb_markets

    # For each market, invest +amount if price > 50%, -amount if price < 50%
    for market_info in market_data.values():
        current_price = market_info.current_price

        if current_price is not None:
            if current_price > 0.5:
                amount = amount_per_market
                rationale = (
                    f"Price {current_price:.2f} > 50%, betting positive {amount:.3f}"
                )
            else:
                amount = -amount_per_market
                rationale = (
                    f"Price {current_price:.2f} < 50%, betting negative {amount:.3f}"
                )
        else:
            amount = 0.0
            rationale = "No price data available, no bet"

        model_decision = SingleInvestmentDecision(
            rationale=rationale,
            estimated_probability=current_price or 0.5,
            bet=amount,
            confidence=6,
        )

        market_decision = MarketInvestmentDecision(
            market_id=market_info.id,
            decision=model_decision,
        )
        market_investments.append(market_decision)

    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=market_investments,
        unallocated_capital=0.0,
        token_usage=None,
        full_response={"model_type": model_info.model_id},
        sources_google=None,
        sources_visit_webpage=None,
    )


def _create_volume_proportional_decisions(
    market_data: dict[str, MarketInfo], event: Event, model_info: ModelInfo
) -> CompleteMarketInvestmentDecisions:
    """Bet on the most likely outcome but split across markets proportionally by volume."""
    market_investments = []
    per_event_allocation = 1.0

    # Get market volumes and find total volume
    market_volumes = {}
    total_volume = 0.0

    for market in event.markets:
        volume = market.volumeNum or 0.0
        market_volumes[market.id] = volume
        total_volume += volume

    # If no volume data, use equal weights
    if total_volume == 0.0:
        return _create_most_likely_outcome_decisions(
            market_data=market_data, model_info=model_info
        )

    # Allocate proportionally by volume with directional betting based on price
    for market_info in market_data.values():
        market_id = market_info.id
        volume_proportion = market_volumes[market_id] / total_volume
        base_amount = per_event_allocation * volume_proportion
        current_price = market_info.current_price

        if current_price is not None:
            if current_price < 0.5:
                amount = base_amount  # Positive bet when price < 50%
                rationale = f"Volume-proportional allocation: {volume_proportion:.2%} of capital based on volume {market_volumes[market_id]:.0f}, price {current_price:.2f} < 50% (positive bet)"
            else:
                amount = -base_amount  # Negative bet when price >= 50%
                rationale = f"Volume-proportional allocation: {volume_proportion:.2%} of capital based on volume {market_volumes[market_id]:.0f}, price {current_price:.2f} >= 50% (negative bet)"
        else:
            amount = 0.0
            rationale = f"Volume-proportional allocation: {volume_proportion:.2%} of capital based on volume {market_volumes[market_id]:.0f}, no price data available"

        model_decision = SingleInvestmentDecision(
            rationale=rationale,
            estimated_probability=current_price or 0.5,
            bet=amount,
            confidence=6,
        )
        market_decision = MarketInvestmentDecision(
            market_id=market_info.id,
            decision=model_decision,
        )
        market_investments.append(market_decision)

    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=market_investments,
        unallocated_capital=0.0,
        token_usage=None,
        full_response={"model_type": model_info.model_id},
        sources_google=None,
        sources_visit_webpage=None,
    )


def _process_event_investment(
    model_info: ModelInfo,
    event: Event,
    target_date: date,
    price_history_limit: int = 20,
) -> EventInvestmentDecisions | None:
    """Process investment decisions for all relevant markets."""
    logger.info(f"Processing event: {event.title} with {len(event.markets)} markets")
    backward_mode = is_backward_mode(target_date)

    timing = Timing(start_time=time.time())

    # Prepare market data for all markets
    market_data: dict[str, MarketInfo] = {}

    for market in event.markets:
        if market.prices is None:
            raise ValueError(
                "markets are supposed to be filtered, this should not be possible"
            )
        # Check if market is closed and get price data
        if market.prices is not None and target_date in market.prices.index:
            if backward_mode:
                price_data = market.prices.loc[:target_date].dropna()
            else:
                price_data = market.prices.dropna()
            # Convert to daily data for LLM prompt
            price_data = Market.convert_to_daily_data(price_data)
            # Limit price history
            if len(price_data) > price_history_limit:
                price_data = price_data.tail(price_history_limit)
            recent_prices = price_data.to_string(index=True, header=False)
            current_price = float(market.prices.loc[target_date])
            is_closed = False
        else:
            # Market is closed - get all available historical prices
            if market.prices is not None and len(market.prices) > 0:
                price_data = market.prices.dropna()
                # Convert to daily data for LLM prompt
                price_data = Market.convert_to_daily_data(price_data)
                # Limit price history
                if len(price_data) > price_history_limit:
                    price_data = price_data.tail(price_history_limit)
                recent_prices = price_data.to_string(index=True, header=False)
                current_price = float(market.prices.dropna().iloc[-1])
            else:
                recent_prices = "No price data available"
                current_price = None
            is_closed = True

        assert len(market.outcomes) == 2, (
            f"Needed 2 outcomes for market {market.id}, got {len(market.outcomes)} (we need one 'bet for' and one 'bet against')"
        )

        market_data[market.id] = MarketInfo(
            id=market.id,
            question=market.question,
            description=market.description,
            recent_prices=recent_prices,
            current_price=current_price,
            is_closed=is_closed,
            outcomes=[outcome.name for outcome in market.outcomes],
            price_outcome_name=market.price_outcome_name or "Yes",
        )

    # Create summaries for all markets
    market_summaries = []
    last_description_used = ""
    for market_info in market_data.values():
        price_outcome_name = market_info.price_outcome_name
        description = market_info.description
        if not description or description == last_description_used:
            description = "Description: Same as the previous market."
        else:
            last_description_used = description
            description = (
                f"Description:</market_description>{description}</market_description>"
            )

        summary = f"""<market_{market_info.id}>
Market ID: {market_info.id}
Question: {market_info.question}
{description}
Possible outcomes: {", ".join(market_info.outcomes)}
Price history for the outcome "{price_outcome_name}" (betting a positive amount means betting for this outcome, betting a negative amount means betting against this outcome):
{market_info.recent_prices}
Most recent price for "{price_outcome_name}": {market_info.current_price}
</market_{market_info.id}>"""
        market_summaries.append(summary)

    full_question = f"""
You are an expert prediction-market analyst. You have been given an amount of USD $1.0 to allocate on the following event from the prediction market Polymarket.

<event_details>
- Date: {target_date.strftime("%B %d, %Y")}
- Title: {event.title}
- Description: {event.description}
- Available Markets: {len(market_data)} markets, see below.
</event_details>

<available_markets>
{"\n\n".join(market_summaries)}
</available_markets>

<analysis_guidelines>
- Use web search to gather up-to-date information about this event
- Be critical of any sources, and be cautious of sensationalized headlines or partisan sources
- If some web search results appear to indicate the event's outcome directly, that would be weird because the event should still be unresolved : so double-check that they do not refer to another event, for instance unrelated or long past.
- Only place a bet when you estimate that the market is mispriced.
</analysis_guidelines>

<capital_allocation_rules>
- You have exactly 1.0 dollars to allocate. Use the "bet" field to allocate your capital. Negative means you buy the second outcome of the market (outcomes are listed in each market description), but they still count in absolute value towards the 1.0 dollar allocation.
- For EACH market, specify your bet. Provide exactly:
{BET_DESCRIPTION}
- You can of course choose not to bet on some markets: then the bet should be 0.0.
- The sum of all absolute values of bets + unallocated_capital must equal 1.0. Example: If you bet 0.3 in market A, -0.2 in market B, and nothing on market C, your unallocated_capital should be 0.5, such that the sum is 0.3 + 0.2 + 0.5 = 1.0.
</capital_allocation_rules>"""

    # Save prompt to file if date_output_path is provided
    model_result_path = model_info.get_model_result_path(target_date)
    prompt_file = model_result_path / f"{event.id}_prompt_event.txt"
    write_to_storage(prompt_file, full_question)
    logger.info(f"Saved prompt to {prompt_file}")

    if model_info.model_id == "test_random":
        complete_market_investment_decisions = _create_random_betting_decisions(
            market_data, model_info
        )
    elif model_info.model_id == "most_likely_outcome":
        complete_market_investment_decisions = _create_most_likely_outcome_decisions(
            market_data, model_info
        )
    elif model_info.model_id == "most_likely_volume_proportional":
        complete_market_investment_decisions = _create_volume_proportional_decisions(
            market_data, event, model_info
        )
    elif (
        model_info.inference_provider == "openai"
        and "deep-research" in model_info.model_id
    ):
        complete_market_investment_decisions = run_openai_deep_research(
            model_id=model_info.model_id,
            question=full_question,
            model_info=model_info,
            target_date=target_date,
            event_id=event.id,
        )
    elif (
        model_info.inference_provider == "perplexity"
        and "deep-research" in model_info.model_id
    ):
        complete_market_investment_decisions = run_perplexity_deep_research(
            model_id=model_info.model_id,
            question=full_question,
            model_info=model_info,
            target_date=target_date,
            event_id=event.id,
        )
    else:
        complete_market_investment_decisions = run_smolagents(
            model_info=model_info,
            question=full_question,
            cutoff_date=target_date if backward_mode else None,
            search_provider="bright_data",
            max_steps=20,
        )
    for (
        market_decision
    ) in complete_market_investment_decisions.market_investment_decisions:
        market_decision.market_question = market_data[
            market_decision.market_id
        ].question

    # Validate all market IDs are correct
    valid_market_ids = set(market_data.keys())
    for (
        market_decision
    ) in complete_market_investment_decisions.market_investment_decisions:
        if market_decision.market_id not in valid_market_ids:
            logger.error(
                f"Invalid market ID {market_decision.market_id} in decisions for event {event.id}. Valid IDs: {list(valid_market_ids)}"
            )
            return None

    full_response_json = complete_market_investment_decisions.full_response

    # Determine agent type - use deepresearch for deep research models, otherwise use model_info.agent_type
    if (
        model_info.inference_provider == "openai"
        and "deep-research" in model_info.model_id
    ) or (
        model_info.inference_provider == "perplexity"
        and "deep-research" in model_info.model_id
    ):
        agent_type = "deepresearch"
    else:
        agent_type = model_info.agent_type

    # Create and write FullModelResult to file
    full_model_result = FullModelResult(
        model_id=model_info.model_id,
        event_id=event.id,
        target_date=date_to_string(target_date),
        agent_type=agent_type,
        full_result_listdict=full_response_json,
    )
    model_result_path = model_info.get_model_result_path(target_date)
    full_response_file = model_result_path / f"{event.id}_full_response.json"
    write_to_storage(full_response_file, full_model_result.model_dump_json(indent=2))

    timing.end_time = time.time()
    event_decisions = EventInvestmentDecisions(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_investment_decisions=complete_market_investment_decisions.market_investment_decisions,
        unallocated_capital=complete_market_investment_decisions.unallocated_capital,
        token_usage=complete_market_investment_decisions.token_usage,
        timing=timing,
        sources_google=complete_market_investment_decisions.sources_google,
        sources_visit_webpage=complete_market_investment_decisions.sources_visit_webpage,
    )

    return event_decisions


def _process_single_model(
    events: list[Event],
    target_date: date,
    model_info: ModelInfo,
    force_rewrite: bool = False,
) -> ModelInvestmentDecisions:
    """Process investments for all events for a model."""
    all_event_decisions = []

    for event in events:
        # Check if event file already exists for this model
        model_result_path = model_info.get_model_result_path(target_date)
        event_file_path = model_result_path / f"{event.id}_event_decisions.json"

        if file_exists_in_storage(event_file_path, force_rewrite=force_rewrite):
            # File exists and we're not forcing rewrite, so load existing result
            logger.info(
                f"Loading existing event result for {event.title} for model {model_info.model_id} from {event_file_path}"
            )
            existing_content = read_from_storage(event_file_path)
            try:
                event_decisions = EventInvestmentDecisions.model_validate_json(
                    existing_content
                )
            except ValidationError as e:
                logger.error(
                    f"Failed to parse existing event result (Pydantic error): {e}. Re-processing event."
                )
                # Fall through to process the event normally
                event_decisions = None

            if isinstance(event_decisions, EventInvestmentDecisions):
                all_event_decisions.append(event_decisions)
                continue

        logger.info(f"Processing event: {event.title}")
        event_decisions: EventInvestmentDecisions = _process_event_investment(
            model_info=model_info,
            event=event,
            target_date=target_date,
        )

        if event_decisions is None:
            continue

        event_content = event_decisions.model_dump_json(indent=2)
        write_to_storage(event_file_path, event_content)
        logger.info(f"Saved event result to {event_file_path}")
        all_event_decisions.append(event_decisions)

    model_result = ModelInvestmentDecisions(
        model_id=model_info.model_id,
        model_info=model_info,
        target_date=target_date,
        decision_datetime=datetime.now(),
        event_investment_decisions=all_event_decisions,
    )

    model_result._save_model_result()
    return model_result


def run_agent_investments(
    models: list[ModelInfo],
    events: list[Event],
    target_date: date,
    force_rewrite: bool = False,
) -> list[ModelInvestmentDecisions]:
    """Launch agent investments for events on a specific date."""
    logger.info(f"Running agent investments for {len(models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")

    results = []
    for model in models:
        logger.info(f"Processing model: {model.model_pretty_name}")
        model_result = _process_single_model(
            model_info=model,
            events=events,
            target_date=target_date,
            force_rewrite=force_rewrite,
        )
        results.append(model_result)

    return results
