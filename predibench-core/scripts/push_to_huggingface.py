#!/usr/bin/env python3
"""
Script to push model investment decisions to Hugging Face dataset.
This script reads model_investment_decisions.json files and creates a dataset
that can be viewed as a DataFrame on Hugging Face.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from datasets import Dataset
from huggingface_hub import login


def load_model_investment_decision(file_path: Path) -> Dict[str, Any]:
    """Load a single model investment decision JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def flatten_investment_decision(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten the nested structure into rows for DataFrame representation.
    Each row represents one market investment decision within an event.
    """
    rows = []

    # Extract base model information
    model_id = data.get("model_id", "")
    target_date = data.get("target_date", "")
    decision_datetime = data.get("decision_datetime", "")

    # Extract model info if present
    model_info = data.get("model_info", {})
    model_pretty_name = model_info.get("model_pretty_name", "")
    inference_provider = model_info.get("inference_provider", "")
    company_pretty_name = model_info.get("company_pretty_name", "")
    open_weights = model_info.get("open_weights", False)
    agent_type = model_info.get("agent_type", "code")

    # Process each event
    for event in data.get("event_investment_decisions", []):
        event_id = event.get("event_id", "")
        event_title = event.get("event_title", "")
        event_description = event.get("event_description", "")
        unallocated_capital = event.get("unallocated_capital", 0.0)

        # Token usage and timing
        token_usage = (
            json.dumps(event.get("token_usage", {}))
            if event.get("token_usage")
            else None
        )
        timing = json.dumps(event.get("timing", {})) if event.get("timing") else None

        # Sources
        sources_google = (
            json.dumps(event.get("sources_google", []))
            if event.get("sources_google")
            else None
        )
        sources_visit_webpage = (
            json.dumps(event.get("sources_visit_webpage", []))
            if event.get("sources_visit_webpage")
            else None
        )

        # Event returns
        event_returns = (
            json.dumps(event.get("returns", {})) if event.get("returns") else None
        )

        # Process each market decision within the event
        for market_decision in event.get("market_investment_decisions", []):
            market_id = market_decision.get("market_id", "")
            market_question = market_decision.get("market_question", "")

            # Decision details
            decision = market_decision.get("decision", {})
            rationale = decision.get("rationale", "")
            estimated_probability = decision.get("estimated_probability", 0.0)
            bet = decision.get("bet", 0.0)
            confidence = decision.get("confidence", 0)

            # Market returns and metrics
            net_gains_at_decision_end = market_decision.get("net_gains_at_decision_end")
            market_returns = (
                json.dumps(market_decision.get("returns", {}))
                if market_decision.get("returns")
                else None
            )
            brier_score_pair = (
                json.dumps(market_decision.get("brier_score_pair_current", []))
                if market_decision.get("brier_score_pair_current")
                else None
            )

            row = {
                # Model metadata
                "model_id": model_id,
                "model_pretty_name": model_pretty_name,
                "inference_provider": inference_provider,
                "company_pretty_name": company_pretty_name,
                "open_weights": open_weights,
                "agent_type": agent_type,
                "target_date": target_date,
                "decision_datetime": decision_datetime,
                # Event metadata
                "event_id": event_id,
                "event_title": event_title,
                "event_description": event_description,
                "event_unallocated_capital": unallocated_capital,
                "event_token_usage": token_usage,
                "event_timing": timing,
                "event_sources_google": sources_google,
                "event_sources_visit_webpage": sources_visit_webpage,
                "event_returns": event_returns,
                # Market decision
                "market_id": market_id,
                "market_question": market_question,
                "decision_rationale": rationale,
                "decision_estimated_probability": estimated_probability,
                "decision_bet": bet,
                "decision_confidence": confidence,
                "market_net_gains_at_decision_end": net_gains_at_decision_end,
                "market_returns": market_returns,
                "market_brier_score_pair": brier_score_pair,
            }

            rows.append(row)

    return rows


def collect_all_decisions(bucket_path: Path) -> pd.DataFrame:
    """Collect all model investment decisions from the bucket directory."""
    all_rows = []

    # Find all model_investment_decisions.json files
    json_files = list(bucket_path.glob("*/*/model_investment_decisions.json"))

    print(f"Found {len(json_files)} model investment decision files")

    for json_file in json_files:
        try:
            print(f"Processing: {json_file}")
            data = load_model_investment_decision(json_file)
            rows = flatten_investment_decision(data)
            all_rows.extend(rows)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

    # Create DataFrame
    df = pd.DataFrame(all_rows)

    # Sort by date and model
    if not df.empty and "target_date" in df.columns:
        df = df.sort_values(["target_date", "model_id", "event_id", "market_id"])

    return df


def push_to_huggingface(df: pd.DataFrame, dataset_name: str, token: str = None):
    """
    Push the DataFrame to Hugging Face as a dataset.
    This function only uploads data, it does not modify the source.
    """
    if token:
        login(token=token)

    # Convert DataFrame to Hugging Face Dataset
    dataset = Dataset.from_pandas(df)

    # Push to hub (this creates or updates the dataset)
    dataset.push_to_hub(
        dataset_name,
        private=False,  # Make it public
        commit_message="Update model investment decisions dataset",
    )

    print(
        f"Successfully pushed dataset to: https://huggingface.co/datasets/{dataset_name}"
    )
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")


def main():
    parser = argparse.ArgumentParser(
        description="Push model investment decisions to Hugging Face dataset"
    )
    parser.add_argument(
        "--bucket-path",
        type=str,
        default="/Users/charlesazam/charloupioupiou/market-bench/bucket-prod/model_results",
        help="Path to the bucket directory containing model results",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="PresageLabs/predibench",
        help="Name of the Hugging Face dataset (format: username/dataset-name)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Hugging Face API token (optional if already logged in)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the data without uploading to Hugging Face",
    )

    args = parser.parse_args()

    # Collect all decisions
    bucket_path = Path(args.bucket_path)
    if not bucket_path.exists():
        print(f"Error: Bucket path does not exist: {bucket_path}")
        return

    print(f"Collecting data from: {bucket_path}")
    df = collect_all_decisions(bucket_path)

    if df.empty:
        print("No data found to upload")
        return

    # Show preview
    print("\nDataset Preview:")
    print(f"Shape: {df.shape}")
    print("\nFirst few rows:")
    print(df.head())
    print("\nData types:")
    print(df.dtypes)

    if args.preview:
        print("\nPreview mode - not uploading to Hugging Face")
        # Save a local CSV for inspection
        preview_file = "predibench_preview.csv"
        df.to_csv(preview_file, index=False)
        print(f"Preview saved to: {preview_file}")
    else:
        # Push to Hugging Face
        print(f"\nUploading to Hugging Face dataset: {args.dataset_name}")
        push_to_huggingface(df, args.dataset_name, args.token)


if __name__ == "__main__":
    main()
