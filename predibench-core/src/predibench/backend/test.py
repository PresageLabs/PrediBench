"""
Comprehensive data computation for backend caching.
This module pre-computes all data needed for all backend API endpoints.
"""

from predibench.backend.compute_profits import _compute_profits
from predibench.backend.data_loader import (
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.data_model import (
    BackendData,
    EventBackend,
)
from predibench.backend.events import get_non_duplicated_events
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import get_market_prices_dataframe
from predibench.logger_config import get_logger
from predibench.utils import _to_date_index

logger = get_logger(__name__)


def get_data_for_backend(
    recompute_bets_with_kelly_criterion: bool = False,
    ignored_providers: list[str] | None = None,
) -> BackendData:
    """
    Pre-compute all data needed for backend API endpoints.

    This function loads all data sources only once and computes everything needed
    for maximum performance at runtime.

    Args:
        recompute_bets_with_kelly_criterion: Whether to recompute all bets using Kelly criterion
        ignored_providers: List of provider names to ignore (case-insensitive)
    """
    logger.info("Starting comprehensive backend data computation...")

    # Step 1: Load all base data sources (load once, use everywhere)
    logger.info("Loading base data sources...")
    model_decisions = load_investment_choices_from_google()  # Load once

    # Filter out models from ignored providers
    if ignored_providers:
        ignored_providers_lower = [provider.lower() for provider in ignored_providers]
        original_count = len(model_decisions)
        model_decisions = [
            decision
            for decision in model_decisions
            if decision.model_info.inference_provider.lower()
            not in ignored_providers_lower
        ]
        filtered_count = len(model_decisions)
        logger.info(
            f"Filtered {original_count - filtered_count} model decisions from ignored providers: {ignored_providers}"
        )
        logger.info(f"Remaining model decisions: {filtered_count}")
    _saved_events = load_saved_events()  # Load once
    events = get_non_duplicated_events(_saved_events)
    logger.info("Loading market prices...")
    market_prices = load_market_prices(events)  # Load once
    prices_df = get_market_prices_dataframe(market_prices)  # Load once
    prices_df = prices_df.sort_index()
    # prices_df = prices_df.resample("D").last()  # Do this BEFORE _to_date_index
    prices_df = _to_date_index(prices_df)

    # Step 1.5: Convert Polymarket Event models to backend Event models
    backend_events = [EventBackend.from_event(e) for e in events]

    # Step 2: Optionally recompute bets using Kelly at decision time, then
    # compute ModelPerformanceBackend for each model
    logger.info("Computing model performance data (per day + per event)...")
    # When recomputing, apply Kelly using the original market price series
    # at the model's decision date; only bets are rescaled, unallocated stays.

    enriched_model_decisions, performance_per_model = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
        recompute_bets_with_kelly_criterion=recompute_bets_with_kelly_criterion,
    )

    # Step 3: Compute leaderboard from performance
    logger.info("Building leaderboard from performance data...")
    leaderboard = get_leaderboard(list(performance_per_model.values()))

    logger.info("Finished computing comprehensive backend data!")

    return BackendData(
        leaderboard=leaderboard,
        events=backend_events,
        performance_per_model=performance_per_model,
        model_decisions=enriched_model_decisions,
    )
