#!/usr/bin/env python3
"""
Script to pre-compute and cache all backend data for maximum performance.

This script computes all data needed for the backend API endpoints and saves
it to storage using the storage utilities.
"""

import json
from datetime import datetime

import typer
from predibench.backend.comprehensive_data import get_data_for_backend
from predibench.common import DATA_PATH
from predibench.storage_utils import write_to_storage

app = typer.Typer(help="Generate precomputed backend cache data")


@app.command()
def main(
    recompute_bets_with_kelly_criterion: bool = typer.Option(
        False,
        "--recompute-all-bets",
        help=(
            "Recompute each market bet from model-estimated odds vs market price using Kelly sizing"
        ),
    ),
    ignored_providers: list[str] = typer.Option(
        [],
        "--ignored-providers",
        help="List of provider names to ignore when generating cache (e.g., 'openai', 'anthropic')",
    ),
):
    """Compute and persist backend cache data for the API."""
    typer.echo("=== Backend Cache Generation ===")
    typer.echo(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if recompute_bets_with_kelly_criterion:
        typer.echo("RECOMPUTING ALL BETS")

    # Compute all backend data
    typer.echo("\n1. Computing comprehensive backend data...")
    if ignored_providers:
        typer.echo(f"Ignoring providers: {', '.join(ignored_providers)}")
    backend_data = get_data_for_backend(
        recompute_bets_with_kelly_criterion=recompute_bets_with_kelly_criterion,
        ignored_providers=ignored_providers,
    )

    # Convert to JSON-serializable format
    typer.echo("\n2. Converting to JSON format...")
    backend_data_dict = backend_data.model_dump()
    json_content = json.dumps(backend_data_dict, indent=2, default=str)

    # Save using storage utilities
    cache_file_path = DATA_PATH / "backend_cache.json"
    typer.echo("\n3. Saving to storage...")
    write_to_storage(cache_file_path, json_content)

    # Print summary statistics
    typer.echo("\n=== Cache Generation Complete ===")
    typer.echo(f"Generated at: {datetime.now()}")

    typer.echo("\nData summary:")
    typer.echo(f"  - Leaderboard entries: {len(backend_data.leaderboard)}")
    typer.echo(f"  - Events: {len(backend_data.events)}")
    typer.echo(f"  - Model results: {len(backend_data.model_decisions)}")

    typer.echo("\n✓ Backend cache saved successfully!")
    typer.echo(f"Cache location: {cache_file_path}")


if __name__ == "__main__":
    app()
