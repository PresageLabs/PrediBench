import json
import os
import textwrap
from datetime import date
from typing import Any

import numpy as np
import requests
from openai import OpenAI
from predibench.agent.dataclasses import (
    MarketInvestmentDecision,
    ModelInfo,
    SingleModelDecision,
)
from predibench.logger_config import get_logger
from pydantic import BaseModel
from smolagents import (
    ChatMessage,
    LiteLLMModel,
    TokenUsage,
    Tool,
    ToolCallingAgent,
    VisitWebpageTool,
    tool,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = get_logger(__name__)


class GoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs Google web search and returns top results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
    }
    output_type = "string"

    def __init__(self, provider: str, cutoff_date: date | None, api_key: str):
        super().__init__()
        self.provider = provider
        self.organic_key = "organic_results" if provider == "serpapi" else "organic"
        self.api_key = api_key
        self.cutoff_date = cutoff_date

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def forward(self, query: str) -> str:
        if self.provider == "serpapi":
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "google_domain": "google.com",
            }
            if self.cutoff_date is not None:
                params["tbs"] = f"cdr:1,cd_max:{self.cutoff_date.strftime('%m/%d/%Y')}"

            response = requests.get("https://serpapi.com/search.json", params=params)
        else:
            payload = {
                "q": query,
            }
            if self.cutoff_date is not None:
                payload["tbs"] = f"cdr:1,cd_max:{self.cutoff_date.strftime('%m/%d/%Y')}"

            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            response = requests.post(
                "https://google.serper.dev/search", json=payload, headers=headers
            )

        if response.status_code == 200:
            results = response.json()
        else:
            logger.error(f"Error response: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            raise ValueError(response.json())

        if self.organic_key not in results.keys():
            raise Exception(
                f"No results found for query: '{query}'. Use a less restrictive query."
            )
        if len(results[self.organic_key]) == 0:
            return f"No results found for '{query}'. Try with a more general query."

        web_snippets = []
        if self.organic_key in results:
            for idx, page in enumerate(results[self.organic_key]):
                date_published = ""
                if "date" in page:
                    date_published = "\nDate published: " + page["date"]

                source = ""
                if "source" in page:
                    source = "\nSource: " + page["source"]

                snippet = ""
                if "snippet" in page:
                    snippet = "\n" + page["snippet"]

                redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
                web_snippets.append(redacted_version)

        return f"## Search Results for '{query}'\n" + "\n\n".join(web_snippets)


@tool
def final_answer(
    market_decisions: list[dict], unallocated_capital: float
) -> tuple[list[MarketInvestmentDecision], float]:
    """
    Use this tool to validate and return the final event decisions for all relevant markets.
    Provide decisions for all markets you want to bet on.

    Args:
        market_decisions (list[dict]): List of market decisions. Each dict should contain:
            - market_id (str): The market ID
            - rationale (str): Reasoning for the decision
            - odds (float): Your probability assessment (0.0 to 1.0) for the main outcome of the market (usually the "Yes" outcome)
            - bet (float): Your bet (-1.0 to 1.0) for the market : if you estimate the main outcome (usually the "Yes" outcome) to be overvalued/undervalued, place your bet accordingly!
            - confidence (float): Your confidence in your decision (0.0 to 1.0)
        unallocated_capital (float): Fraction of capital not allocated to any bet (0.0 to 1.0)
    """
    # Manual type checks for market_decisions
    if not isinstance(market_decisions, list):
        raise TypeError(f"market_decisions must be a list, got {type(market_decisions).__name__}")
    
    if not market_decisions or len(market_decisions) == 0:
        raise ValueError(
            "No market decisions provided - at least one market decision is required"
        )
    
    for i, decision in enumerate(market_decisions):
        if not isinstance(decision, dict):
            raise TypeError(f"market_decisions[{i}] must be a dict, got {type(decision).__name__}")
    
    # Manual type checks for unallocated_capital
    if not isinstance(unallocated_capital, (int, float)):
        raise TypeError(f"unallocated_capital must be a float or int, got {type(unallocated_capital).__name__}")
    
    try:
        unallocated_capital = float(unallocated_capital)
    except (ValueError, TypeError) as e:
        raise TypeError(f"unallocated_capital cannot be converted to float: {e}")

    validated_decisions = []
    total_allocated = 0.0
    assert unallocated_capital >= 0.0, "Unallocated capital cannot be negative"

    for decision_dict in market_decisions:
        # Check required fields
        assert "market_id" in decision_dict, (
            "A key 'market_id' is required for each market decision"
        )
        assert "rationale" in decision_dict, (
            "A key 'rationale' is required for each market decision"
        )
        assert "odds" in decision_dict, (
            "A key 'odds' is required for each market decision"
        )
        assert "bet" in decision_dict, (
            "A key 'bet' is required for each market decision"
        )
        assert "confidence" in decision_dict, (
            "A key 'confidence' is required for each market decision"
        )

        # Validate market_id is not empty
        if not decision_dict["market_id"] or decision_dict["market_id"].strip() == "":
            raise ValueError("Market ID cannot be empty or whitespace only")

        # Validate rationale is not empty
        if not decision_dict["rationale"] or decision_dict["rationale"].strip() == "":
            raise ValueError(
                f"Rationale cannot be empty for market {decision_dict['market_id']}"
            )
        assert -1.0 <= decision_dict["bet"] <= 1.0, (
            f"Your bet must be between -1.0 and 1.0, got {decision_dict['bet']} for market {decision_dict['market_id']}"
        )
        assert 0.0 <= decision_dict["odds"] <= 1.0, (
            f"Your estimated odds must be between 0.0 and 1.0, got {decision_dict['odds']} for market {decision_dict['market_id']}"
        )
        assert 0.0 <= decision_dict["confidence"] <= 1.0, (
            f"Your confidence must be between 0.0 and 1.0, got {decision_dict['confidence']} for market {decision_dict['market_id']}"
        )

        model_decision = SingleModelDecision(
            rationale=decision_dict["rationale"],
            odds=decision_dict["odds"],
            bet=decision_dict["bet"],
            confidence=decision_dict["confidence"],
        )
        total_allocated += np.abs(decision_dict["bet"])

        market_decision = MarketInvestmentDecision(
            market_id=decision_dict["market_id"],
            model_decision=model_decision,
        )
        validated_decisions.append(market_decision)

    # assert total_allocated + unallocated_capital == 1.0, (
    #     f"Total capital allocation, calculated as the sum of all absolute value of bets, must equal 1.0, got {total_allocated + unallocated_capital:.3f} (allocated: {total_allocated:.3f}, unallocated: {unallocated_capital:.3f})"
    # ) @ NOTE: models like gpt-4.1 are too dumb to respect this constraint, let's just enforce it a-posteriori with rescaling if needed.
    # if total_allocated + unallocated_capital != 1.0:
    #     for decision in validated_decisions:
    #         decision.model_decision.bet = decision.model_decision.bet / (
    #             total_allocated + unallocated_capital
    #         )
    # NOTE: don't rescale in the end

    return validated_decisions, unallocated_capital


class CompleteMarketInvestmentDecisions(BaseModel):
    market_investment_decisions: list[MarketInvestmentDecision]
    unallocated_capital: float
    full_response: Any
    token_usage: TokenUsage | None = None


class ListMarketInvestmentDecisions(BaseModel):
    market_investment_decisions: list[MarketInvestmentDecision]
    unallocated_capital: float


def run_smolagents(
    model_info: ModelInfo,
    question: str,
    cutoff_date: date | None,
    search_provider: str,
    search_api_key: str,
    max_steps: int,
) -> CompleteMarketInvestmentDecisions:
    """Run smolagent for event-level analysis with structured output."""
    model_client = model_info.client
    assert model_client is not None, "Model client is not set"

    prompt = f"""{question}
        
Use the final_answer tool to validate your output before providing the final answer.
The final_answer tool must contain the arguments rationale and decision.
"""
    if cutoff_date is not None:
        assert cutoff_date < date.today()

    tools = [
        GoogleSearchTool(
            provider=search_provider, cutoff_date=cutoff_date, api_key=search_api_key
        ),
        VisitWebpageTool(),
        final_answer,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model_client, max_steps=max_steps, return_full_result=True
    )

    full_result = agent.run(prompt)
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=full_result.output[0],
        unallocated_capital=full_result.output[1],
        full_response=full_result.steps,
        token_usage=full_result.token_usage,
    )


def structure_final_answer(
    research_output: str, structured_output_model_id: str = "gpt-4.1"
) -> tuple[list[MarketInvestmentDecision], float]:
    structured_model = LiteLLMModel(model_id=structured_output_model_id)

    structured_prompt = textwrap.dedent(f"""
        Based on the following research output, extract the investment decisions for each market:
        
        {research_output}
        
        You must provide a list of market decisions. Each decision should include:
        1. market_id: The ID of the market
        2. reasoning: Your reasoning for this decision
        3. probability_assessment: Your probability assessment (0.0 to 1.0)
        4. confidence_in_assessment: Your confidence level (0.0 to 1.0)
        5. direction: "buy_yes", "buy_no", or "nothing"
        6. amount: Fraction of capital to bet (0.0 to 1.0)
        7. confidence: Your confidence in this decision (0.0 to 1.0)

        The sum of all amounts must not exceed 1.0.
    """)
    structured_output = structured_model.generate(
        [ChatMessage(role="user", content=structured_prompt)],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": ListMarketInvestmentDecisions.model_json_schema(),
            },
        },
    )

    parsed_output = json.loads(structured_output.content)
    market_investment_decisions_json = parsed_output["market_investment_decisions"]
    unallocated_capital = parsed_output["unallocated_capital"]
    return (
        [
            MarketInvestmentDecision(**decision)
            for decision in market_investment_decisions_json
        ],
        unallocated_capital,
    )


def run_openai_deep_research(
    model_id: str,
    question: str,
) -> CompleteMarketInvestmentDecisions:
    client = OpenAI(timeout=3600)

    full_response = client.responses.create(
        model=model_id,
        input=question
        + "\n\nProvide your detailed analysis and reasoning, then clearly state your final decisions for each market you want to bet on.",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
        ],
    )
    research_output = full_response.output_text

    # Use structured output to get EventDecisions
    structured_market_decisions, unallocated_capital = structure_final_answer(
        research_output
    )
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=structured_market_decisions,
        unallocated_capital=unallocated_capital,
        full_response=full_response,
        token_usage=TokenUsage(
            input_tokens=full_response.usage.input_tokens,
            output_tokens=full_response.usage.output_tokens
            + full_response.usage.output_tokens_details.reasoning_tokens,
        ),
    )


def run_perplexity_deep_research(
    model_id: str,
    question: str,
) -> CompleteMarketInvestmentDecisions:
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
        "Content-Type": "application/json",
    }

    raw_response = requests.post(url, json=payload, headers=headers)
    raw_response.raise_for_status()
    full_response = raw_response.json()
    research_output = full_response["choices"][0]["message"]["content"]
    # TODO: save research_output directly to storage
    structured_market_decisions, unallocated_capital = structure_final_answer(
        research_output
    )
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=structured_market_decisions,
        unallocated_capital=unallocated_capital,
        full_response=full_response,
        token_usage=TokenUsage(
            input_tokens=full_response["usage"]["prompt_tokens"],
            output_tokens=full_response["usage"]["completion_tokens"],
        ),
    )
