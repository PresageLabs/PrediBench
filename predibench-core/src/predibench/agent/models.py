from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from predibench.common import get_date_output_path
from predibench.storage_utils import write_to_storage
from pydantic import AliasChoices, BaseModel, Field
from smolagents import Timing, TokenUsage

# NOTE: price ad odd of the 'yes' on any market should be equal, since normalized to 1


class DataPoint(BaseModel):
    date: str
    value: float

    @staticmethod
    def list_datapoints_from_series(series: pd.Series) -> list["DataPoint"]:
        series = series.sort_index()  # Ensure dates are sorted before conversion

        # Assert that the series is properly sorted
        index_list = list(series.index)
        for i in range(1, len(index_list)):
            assert index_list[i] >= index_list[i - 1], (
                f"Series not sorted at index {i}: {index_list[i - 1]} -> {index_list[i]}"
            )

        result = [
            DataPoint(date=str(date), value=float(value))
            for date, value in series.items()
        ]

        # Assert that the resulting DataPoints are sorted by date string
        for i in range(1, len(result)):
            assert result[i].date >= result[i - 1].date, (
                f"DataPoint not sorted at index {i}: {result[i - 1].date} -> {result[i].date}"
            )

        return result

    @staticmethod
    def series_from_list_datapoints(list: list["DataPoint"]) -> pd.Series:
        return pd.Series(
            [data_point.value for data_point in list],
            index=[data_point.date for data_point in list],
        )


class SingleInvestmentDecision(BaseModel):
    rationale: str = Field(
        ...,
        description="Explanation for your decision and why you think this market is mispriced (or correctly priced if skipping). Write at least a few sentences. If you take a strong bet, make sure to highlight the facts you know/value that the market doesn't.",
    )
    estimated_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Your estimate for the true probability of the market",
        validation_alias=AliasChoices("estimated_probability", "odds"),
    )
    bet: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="The amount in dollars that you bet on this market (can be negative if you want to buy the opposite of the market)",
    )
    confidence: int = Field(
        ...,
        ge=0,
        le=10,
        description="Your confidence in the estimated_probability and your bet. Should be between 0 (absolute uncertainty, you shouldn't bet if you're not confident) and 10 (absolute certainty, then you can bet high).",
    )


class MarketInvestmentDecision(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    market_id: str = Field(..., description="The market ID")
    decision: SingleInvestmentDecision = Field(
        ...,
        description="Model's decision for this market",
        validation_alias=AliasChoices("decision", "model_decision"),
    )
    market_question: str | None = None
    net_gains_at_decision_end: float | None = None
    brier_score_pair_current: tuple[float, float] | None = (
        None  # tuple of (price current, estimated estimated_probability)
    )


class EventInvestmentDecisions(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    event_id: str
    event_title: str
    event_description: str | None = None
    market_investment_decisions: list[
        MarketInvestmentDecision
    ]  # Multiple markets per event
    unallocated_capital: float
    token_usage: TokenUsage | None = None
    timing: Timing | None = None
    sources_google: list[str] | None = None
    sources_visit_webpage: list[str] | None = None
    net_gains_until_next_decision: list[DataPoint] | None = None

    def normalize_investments(
        self,
        apply_kelly_criterion_at_date: date | None = None,
        market_prices: pd.DataFrame | None = None,
    ) -> None:
        """
        Normalize investments at the event level.

        - Default behavior (apply_kelly_bet_criterion=False): keep legacy behavior where
          bets and unallocated capital are jointly scaled so total equals 1.0.
        - Kelly behavior (apply_kelly_bet_criterion=True): compute a Kelly-sized bet
          per market using model probability vs the market price at decision time (if available),
          then rescale only the bets so that total allocated equals (1 - unallocated_capital).
          Unallocated capital remains unchanged.
        """

        def _kelly_signed_bet(estimated_odds: float, market_odds: float) -> float:
            # Guard rails for extreme prices
            if market_odds <= 0:
                return 0.0 if estimated_odds <= market_odds else 1.0
            if market_odds >= 1:
                return 0.0 if estimated_odds >= market_odds else -1.0

            edge = estimated_odds - market_odds
            if abs(edge) < 1e-12:
                return 0.0
            if edge > 0:
                f = edge / (1.0 - market_odds)
                return float(max(0.0, min(1.0, f)))
            else:
                f = (-edge) / market_odds
                return float(-max(0.0, min(1.0, f)))

        if apply_kelly_criterion_at_date is not None and market_prices is not None:
            # Compute Kelly bet per market from provided market price history
            for md in self.market_investment_decisions:
                estimated_odds = float(md.decision.estimated_probability)
                market_price_series = market_prices[md.market_id]
                if market_price_series is None or len(market_price_series) == 0:
                    continue
                # Ensure date index compatibility
                try:
                    idx0 = next(iter(market_price_series.index))
                except StopIteration:
                    continue
                if hasattr(idx0, "date") and not isinstance(idx0, date):
                    # Convert pandas Timestamp or datetime to date
                    market_price_series = market_price_series.copy()
                    market_price_series.index = [
                        ts.date() if hasattr(ts, "date") else ts
                        for ts in market_price_series.index
                    ]
                market_price_series = market_price_series.bfill().ffill()
                if apply_kelly_criterion_at_date not in market_price_series.index:
                    continue
                market_odds = float(
                    market_price_series.loc[apply_kelly_criterion_at_date]
                )
                md.decision.bet = _kelly_signed_bet(estimated_odds, market_odds)

            # Rescale ONLY bets to fit available budget (1 - unallocated_capital)
            available_budget = max(0.0, 1.0 - float(self.unallocated_capital))
            total_allocated = sum(
                abs(md.decision.bet) for md in self.market_investment_decisions
            )
            if total_allocated > 0:
                scale = available_budget / total_allocated
                for md in self.market_investment_decisions:
                    md.decision.bet *= scale
            return

        # Legacy normalization: scale both bets and unallocated capital to sum to 1.0
        total_allocated = sum(
            abs(decision.decision.bet) for decision in self.market_investment_decisions
        )
        total_capital = total_allocated + self.unallocated_capital
        if total_capital != 1.0 and total_capital > 0:
            normalization_factor = 1.0 / total_capital
            for decision in self.market_investment_decisions:
                decision.decision.bet *= normalization_factor
            print(f"Normalized investments for event {self.event_id}")
            self.unallocated_capital *= normalization_factor


class ModelInfo(BaseModel):
    model_id: str
    model_pretty_name: str
    inference_provider: str
    company_pretty_name: str
    open_weights: bool = False
    client: Any | None = None
    agent_type: Literal["code", "toolcalling", "deepresearch"] = "code"

    @staticmethod
    def static_get_model_result_path(model_id: str, target_date: date) -> Path:
        """
        Get the path to the model result for a given model and target date.
        """
        date_output_path = get_date_output_path(target_date)
        model_result_path = date_output_path / model_id.replace("/", "--")
        model_result_path.mkdir(parents=True, exist_ok=True)
        return model_result_path

    def get_model_result_path(self, target_date: date) -> Path:
        """
        Get the path to the model result for a given model and target date.
        """
        return ModelInfo.static_get_model_result_path(
            model_id=self.model_id, target_date=target_date
        )


class ModelInvestmentDecisions(BaseModel):
    model_id: str
    model_info: ModelInfo
    target_date: date
    decision_datetime: datetime
    event_investment_decisions: list[EventInvestmentDecisions]
    # Aggregated portfolio growth (sum of per-event series already divided by 10)
    # starting at 0 on the first date >= decision, until the next decision
    net_gains_until_next_decision: list[DataPoint] | None = None

    def _save_model_result(self) -> None:
        """Save model result to file."""

        model_result_path = self.model_info.get_model_result_path(self.target_date)

        filename = "model_investment_decisions.json"
        filepath = model_result_path / filename

        content = self.model_dump_json(indent=2, exclude={"model_info": {"client"}})
        write_to_storage(filepath, content)

        print(f"Saved model result to {filepath}")
