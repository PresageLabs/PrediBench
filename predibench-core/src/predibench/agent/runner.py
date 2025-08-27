import json
import os
from datetime import date, datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from predibench.agent.dataclasses import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInvestmentDecisions,
    SingleModelDecision,
)
from predibench.agent.smolagents_utils import (
    run_deep_research,
    run_perplexity_deep_research,
    run_smolagents,
)
from predibench.date_utils import is_backward_mode
from predibench.logger_config import get_logger
from predibench.polymarket_api import Event
from predibench.storage_utils import (
<<<<<<< HEAD
    file_exists_in_storage,
    read_from_storage,
    write_to_storage,
)
from pydantic import ValidationError
=======
    write_to_storage,
    file_exists_in_storage,
    read_from_storage,
)
>>>>>>> main
from smolagents import ApiModel

load_dotenv()

logger = get_logger(__name__)


<<<<<<< HEAD
def _upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentDecisions],
    target_date: date,
    dataset_name: str,
    split: str = "train",
    erase_existing: bool = False,
    date_output_path: Path | None = None,
) -> None:
    """Upload investment results to the Hugging Face dataset."""
    # Try to load the existing dataset, handle empty dataset case
    try:
        ds = load_dataset(dataset_name)
    except datasets.data_files.EmptyDatasetError:
        logger.info(f"Dataset {dataset_name} is empty, will create with new data")
        ds = None

    # Prepare new data rows
    new_rows = []
    current_timestamp = datetime.now()

    for model_investment_decision in results_per_model:
        # Extract provider from model_id
        model_id = model_investment_decision.model_id
        if model_id.startswith("openai/"):
            provider = "openai"
        elif model_id.startswith("huggingface/"):
            provider = "huggingface"
        else:
            provider = "unknown"

        # Calculate backward mode
        backward_mode = is_backward_mode(model_investment_decision.target_date)

        for (
            event_investment_decision
        ) in model_investment_decision.event_investment_decisions:
            row = {
                # ModelInvestmentResult fields
                "model_id": model_investment_decision.model_id,
                "agent_name": model_investment_decision.model_id,  # Keep for backward compatibility
                "target_date": model_investment_decision.target_date,
                "date": target_date,  # Keep for backward compatibility
                # EventInvestmentResult fields
                "event_id": event_investment_decision.event_id,
                "event_title": event_investment_decision.event_title,
                "event_description": event_investment_decision.event_description,
                # MarketInvestmentResult fields
                "decisions_per_market": json.dumps(
                    event_investment_decision.market_investment_decisions,
                    default=lambda obj: obj.model_dump()
                    if hasattr(obj, "model_dump")
                    else obj,
                ),
                "timestamp_uploaded": current_timestamp,
                # New columns
                "backward_mode": backward_mode,
                "provider": provider,
            }
            new_rows.append(row)

    if new_rows:
        # Create a new dataset with the new rows
        new_dataset = Dataset.from_list(new_rows)
        # Concatenate with existing dataset using datasets.concatenate_datasets

        # Handle dataset combination based on erase_existing flag
        if erase_existing or ds is None:
            # Either erasing existing data or dataset is empty, just use new data
            combined_dataset = new_dataset
            if erase_existing:
                logger.info(
                    f"Erasing existing dataset and creating fresh dataset with {len(new_dataset)} rows"
                )
            else:
                logger.info(f"Dataset is empty, creating with {len(new_dataset)} rows")
        else:
            try:
                existing_data = ds[split]
                combined_dataset = concatenate_datasets([existing_data, new_dataset])
                logger.info(
                    f"Appending {len(new_dataset)} rows to existing {len(existing_data)} rows"
                )
            except KeyError:
                # Split doesn't exist, just use new data
                combined_dataset = new_dataset
                logger.info(
                    f"Split '{split}' doesn't exist, creating with {len(new_dataset)} rows"
                )

        # Push back to hub as a pull request (safer approach)
        combined_dataset.push_to_hub(
            dataset_name,
            split=split,
        )

        logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")

        # Also save individual CSV files for each model in the date folder
        if date_output_path is not None:
            # Group new_rows by model_id
            model_data = {}
            for row in new_rows:
                model_id = row["model_id"]
                if model_id not in model_data:
                    model_data[model_id] = []
                model_data[model_id].append(row)

            # Save CSV for each model
            for model_id, rows in model_data.items():
                import pandas as pd

                df = pd.DataFrame(rows)
                csv_filename = f"{model_id.replace('/', '--')}.csv"
                csv_path = date_output_path / csv_filename

                # Convert to CSV content
                csv_content = df.to_csv(index=False)
                write_to_storage(csv_path, csv_content)
                logger.info(f"Saved CSV for model {model_id} to {csv_path}")
    else:
        logger.warning("No data to upload to HF dataset")


=======
>>>>>>> main
def save_model_result(
    model_result: ModelInvestmentDecisions,
    date_output_path: Path,
    timestamp_for_saving: str,
) -> None:
    """Save model result to file."""

    filename = f"{model_result.model_id.replace('/', '--')}_{timestamp_for_saving}.json"
    filepath = date_output_path / filename

    content = model_result.model_dump_json(indent=2)
    write_to_storage(filepath, content)

    logger.info(f"Saved model result to {filepath}")


def _process_event_investment(
    model: ApiModel | str,
    event: Event,
    target_date: date,
    date_output_path: Path | None,
    timestamp_for_saving: str,
    price_history_limit: int = 20,
) -> EventInvestmentDecisions | None:
    """Process investment decisions for all relevant markets."""
    logger.info(f"Processing event: {event.title} with {len(event.markets)} markets")
    backward_mode = is_backward_mode(target_date)

    # Prepare market data for all markets
    market_data = {}

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
                # Limit price history
                if len(price_data) > price_history_limit:
                    price_data = price_data.tail(price_history_limit)
                recent_prices = price_data.to_string(index=True, header=False)
                current_price = float(market.prices.dropna().iloc[-1])
            else:
                recent_prices = "No price data available"
                current_price = None
            is_closed = True

        market_info = {
            "id": market.id,
            "question": market.question,
            "description": market.description,
            "recent_prices": recent_prices,
            "current_price": current_price,
            "is_closed": is_closed,
            "price_outcome_name": market.price_outcome_name or "Unknown outcome",
        }
        market_data[market.id] = market_info

    # Create summaries for all markets
    market_summaries = []

    for market_info in market_data.values():
        outcome_name = market_info["price_outcome_name"]

        summary = f"""
Market ID: {market_info["id"]}
Question: {market_info["question"]}
Description: {market_info["description"] or "No description"}
Historical prices for the outcome "{outcome_name}":
{market_info["recent_prices"]}
Last available price for "{outcome_name}": {market_info["current_price"]}
        """
        market_summaries.append(summary)

    full_question = f"""
Date: {target_date.strftime("%B %d, %Y")}

Event: {event.title}

You have access to {len(market_data)} markets related to this event. You must allocate your capital across these markets.

CAPITAL ALLOCATION RULES:
- You have exactly 1.0 dollars to allocate. Negative bets can be done to short the market, but they still count in absolute value towards the 1.0 dollar allocation.
- For EACH market, specify your bet. Provide:
1. market_id: The market ID
2. rationale: Explanation for your decision
4. odds: The odds you think the market will settle at
3. bet: The amount you bet on this market (can be negative if you want to short the market, e.g. if it's overpriced)
- The sum of ALL (absolute value of bets) + unallocated_capital must equal 1.0
- You can choose not to bet on markets with poor edges by setting bets summing to lower than 1 and a non-zero unallocated_capital

AVAILABLE MARKETS:
{"".join(market_summaries)}

Example: If you bet 0.3 on market A, 0.2 on market B, and nothing on market C, your unallocated_capital should be 0.5.
    """

    # Save prompt to file if date_output_path is provided
    if date_output_path:
        model_id = model.model_id if isinstance(model, ApiModel) else model
        prompt_file = (
            date_output_path
            / model_id.replace("/", "--")
            / f"prompt_event_{event.id}_{timestamp_for_saving}.txt"
        )

        write_to_storage(prompt_file, full_question)
        logger.info(f"Saved prompt to {prompt_file}")

    if isinstance(model, str) and model == "test_random":
        # Create random decisions for all markets with capital allocation constraint

        market_decisions = []
        per_event_allocation = 1.0

        number_markets = len(market_data)
        invested_values = np.random.random(number_markets)
        invested_values = (
            per_event_allocation * invested_values / np.sum(invested_values)
        )  # Random numbers that sum to per_event_allocation

        for market_info, invested_value in zip(market_data.values(), invested_values):
            amount = invested_value

            model_decision = SingleModelDecision(
                rationale=f"Random decision for testing market {market_info['id']}",
                odds=np.random.uniform(0.1, 0.9),
                bet=amount,
            )
            market_decision = MarketInvestmentDecision(
                market_id=market_info["id"],
                model_decision=model_decision,
            )
            market_decisions.append(market_decision)

    elif isinstance(model, str) and model == "o3-deep-research":
        market_decisions = run_deep_research(
            model_id="o3-deep-research",
            question=full_question,
        )
    elif isinstance(model, str) and model == "sonar-deep-research":
        market_decisions = run_perplexity_deep_research(
            model_id="sonar-deep-research",
            question=full_question,
        )
    else:
        market_decisions = run_smolagents(
            model=model,
            question=full_question,
            cutoff_date=target_date if backward_mode else None,
            search_provider="serper",
            search_api_key=os.getenv("SERPER_API_KEY"),
            max_steps=20,
        )
    for market_decision in market_decisions:
        market_decision.market_question = market_data[market_decision.market_id][
            "question"
        ]

    # Validate all market IDs are correct
    valid_market_ids = set(market_data.keys())
    for market_decision in market_decisions:
        if market_decision.market_id not in valid_market_ids:
            logger.error(
                f"Invalid market ID {market_decision.market_id} in decisions for event {event.id}. Valid IDs: {list(valid_market_ids)}"
            )
            return None

    event_decisions = EventInvestmentDecisions(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_investment_decisions=market_decisions,
    )

    return event_decisions


def _process_single_model(
    events: list[Event],
    target_date: date,
    date_output_path: Path,
    timestamp_for_saving: str,
    model: ApiModel | str,
    force_rewrite_cache: bool = False,
) -> ModelInvestmentDecisions:
    """Process investments for all events for a model."""
    all_event_decisions = []
    model_id = model.model_id if isinstance(model, ApiModel) else model

    for event in events:
        # Check if event file already exists for this model
        event_file_path = (
            date_output_path / model_id.replace("/", "--") / f"{event.id}.json"
        )

        if file_exists_in_storage(event_file_path, force_rewrite=force_rewrite_cache):
            # File exists and we're not forcing rewrite, so load existing result
            logger.info(
                f"Loading existing event result for {event.title} for model {model_id} from {event_file_path}"
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
        event_decisions = _process_event_investment(
            model=model,
            event=event,
            target_date=target_date,
            date_output_path=date_output_path,
            timestamp_for_saving=timestamp_for_saving,
        )

        if event_decisions is None:
            continue

        event_content = event_decisions.model_dump_json(indent=2)
        write_to_storage(event_file_path, event_content)
        logger.info(f"Saved event result to {event_file_path}")
        all_event_decisions.append(event_decisions)

    model_result = ModelInvestmentDecisions(
        model_id=model_id,
        target_date=target_date,
        event_investment_decisions=all_event_decisions,
    )

    save_model_result(
        model_result=model_result,
        date_output_path=date_output_path,
        timestamp_for_saving=timestamp_for_saving,
    )
    return model_result


def run_agent_investments(
    models: list[ApiModel | str],
    events: list[Event],
    target_date: date,
    date_output_path: Path,
    timestamp_for_saving: str,
    force_rewrite_cache: bool = False,
) -> list[ModelInvestmentDecisions]:
    """Launch agent investments for events on a specific date."""
    logger.info(f"Running agent investments for {len(models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")

    results = []
    for model in models:
        model_name = model.model_id if isinstance(model, ApiModel) else model
        logger.info(f"Processing model: {model_name}")
        model_result = _process_single_model(
            model=model,
            events=events,
            target_date=target_date,
            date_output_path=date_output_path,
            timestamp_for_saving=timestamp_for_saving,
            force_rewrite_cache=force_rewrite_cache,
        )
        results.append(model_result)

    return results
