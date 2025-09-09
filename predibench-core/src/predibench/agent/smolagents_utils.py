import json
import os
import logging
import textwrap
from datetime import date
from typing import Any, Literal
import urllib.parse

import numpy as np
import requests
from openai import OpenAI
from predibench.agent.dataclasses import (
    MarketInvestmentDecision,
    ModelInfo,
    SingleModelDecision,
)
from predibench.logger_config import get_logger
from predibench.storage_utils import write_to_storage, read_from_storage, file_exists_in_storage
from pydantic import BaseModel
from smolagents import (
    ChatMessage,
    CodeAgent,
    LiteLLMModel,
    TokenUsage,
    Tool,
    ToolCallingAgent,
    VisitWebpageTool,
    tool,
)
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)
from markdownify import markdownify as md

logger = get_logger(__name__)

BET_DESCRIPTION = """1. market_id (str): The market ID
2. rationale (str): Explanation for your decision and why you think this market is mispriced (or correctly priced if skipping). Write at least a few sentences. If you take a strong bet, make sure to highlight the facts you know/value that the market doesn't.
3. odds (float, 0 to 1): The odds you think the market will settle at (your true probability estimate)
4. confidence (int, 0 to 10): Your confidence in the odds and your bet. Should be between 0 (absolute uncertainty, you shouldn't bet if you're not confident) and 10 (absolute certainty, then you can bet high).
5. bet (float, -1 to 1): The amount in dollars that you bet on this market (can be negative if you want to buy the opposite of the market)"""


class VisitWebpageToolSaveSources(VisitWebpageTool):
    def __init__(self):
        super().__init__()
        self.sources: list[str] = []

    def forward(self, url: str) -> str:
        content = super().forward(url)
        self.sources.append(url)
        self.sources = list(dict.fromkeys(self.sources))
        return content
    

class GoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs Google web search and returns top results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
    }
    output_type = "string"
    

    def __init__(self, provider: Literal["serpapi", "bright_data", "serper"], cutoff_date: date | None):
        super().__init__()
        self.provider = provider
        if provider == "serpapi":
            self.organic_key = "organic_results"
            self.api_key = os.getenv("SERPAPI_API_KEY")
        elif provider == "bright_data":
            self.organic_key = "organic"
            self.api_key = os.getenv("BRIGHT_SERPER_API_KEY")
        elif provider == "serper":
            self.organic_key = "organic"
            self.api_key = os.getenv("SERPER_API_KEY")
        else:
            raise ValueError(f"Invalid provider: {provider}")
        
        self.cutoff_date = cutoff_date
        self.sources: list[str] = []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
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

        elif self.provider == "bright_data":
            # Define search parameters as dictionary for proper URL encoding
            search_params = {
                "q": query,
                "gl": "US",
                "hl": "en",
                "brd_json": "1"
            }
            
            # Encode parameters properly
            encoded_params = urllib.parse.urlencode(search_params)
            search_url = f"https://google.com/search?{encoded_params}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "method": "GET",
                "zone": "serp_api1",
                "url": search_url,
                "format": "json",
            }
            
            response = requests.post(
                "https://api.brightdata.com/request",
                json=payload,
                headers=headers
            )
        elif self.provider == "serper":
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
            if self.provider == "bright_data":
                raw_result = response.json()
                results = json.loads(raw_result["body"])
            else:
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
                # Handle different date formats for different providers
                if self.provider == "bright_data" and "extensions" in page:
                    # Take the first extension text as date
                    if page["extensions"] and len(page["extensions"]) > 0:
                        first_ext = page["extensions"][0]
                        if isinstance(first_ext, dict) and "text" in first_ext:
                            date_published = "\nDate published: " + first_ext["text"]
                elif "date" in page:
                    date_published = "\nDate published: " + page["date"]

                source = ""
                if "source" in page:
                    source = "\nSource: " + page["source"]

                snippet = ""
                # Handle different field names for different providers
                if self.provider == "bright_data" and "description" in page:
                    snippet = "\n" + page["description"]
                elif "snippet" in page:
                    snippet = "\n" + page["snippet"]

                redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
                web_snippets.append(redacted_version)
                self.sources.append(page["link"])
        self.sources = list(dict.fromkeys(self.sources))
        return f"## Search Results for '{query}'\n" + "\n\n".join(web_snippets)


class BrightDataVisitWebpageTool(Tool):
    name = "visit_webpage_bright_data"
    description = (
        "Visits a webpage using Bright Data's Playwright browser and returns markdown content."
    )
    inputs = {
        "url": {"type": "string", "description": "The webpage URL to fetch."},
    }
    output_type = "string"

    def __init__(self, zone: str | None = None):
        super().__init__()
        # Expect a full Bright Data browser CDP endpoint in env
        self.endpoint = os.getenv("BRIGHT_DATA_BROWSER_ENDPOINT")
        if not self.endpoint:
            raise ValueError(
                "Missing BRIGHT_DATA_BROWSER_ENDPOINT environment variable with the full wss CDP URL."
            )

    def forward(self, url: str) -> str:
        # Create a fresh Playwright session and browser connection for each call
        from playwright.sync_api import sync_playwright

        p = sync_playwright().start()
        browser = None
        page = None
        html = ""
        try:
            browser = p.chromium.connect_over_cdp(self.endpoint)
            page = browser.new_page()
            page.goto(url, timeout=2 * 60_000, wait_until="load")
            html = page.content()
        finally:
            # Cleanup resources regardless of success/failure
            try:
                if page is not None:
                    page.close()
            except Exception:
                pass
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass
            try:
                p.stop()
            except Exception:
                pass

        if not html:
            raise ValueError("Failed to retrieve page content via Bright Data Playwright.")

        markdown_content = md(html, heading_style="ATX")
        return markdown_content


class ScrapeDoVisitWebpageTool(Tool):
    name = "visit_webpage_scrape_do"
    description = (
        "Visits a webpage using Scrape.do and returns markdown content."
    )
    inputs = {
        "url": {"type": "string", "description": "The webpage URL to fetch."},
    }
    output_type = "string"

    def __init__(self, render: bool = True):
        super().__init__()
        self.api_key = os.getenv("SCRAPE_DO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing SCRAPE_DO_API_KEY environment variable for Scrape.do API."
            )
        self.render = render

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
        reraise=True,
    )
    def forward(self, url: str) -> str:
        encoded_target_url = urllib.parse.quote(url, safe="")
        render_param = "true" if self.render else "false"
        scrape_api_url = (
            f"http://api.scrape.do/?url={encoded_target_url}&token={self.api_key}"
            f"&output=markdown&render={render_param}"
        )

        response = requests.get(scrape_api_url)
        if response.status_code != 200:
            logger.error(
                f"Scrape.do error {response.status_code}: {response.text}"
            )
            raise ValueError(response.text)

        # Scrape.do already returns markdown when output=markdown
        return response.text

@tool
def final_answer(
    market_decisions: list[dict], unallocated_capital: float
) -> tuple[list[MarketInvestmentDecision], float]:
    """
    Use this tool to validate and return the final event decisions for all relevant markets.
    Provide decisions for all markets you want to bet on.

    Args:
        market_decisions (list[dict]): List of market decisions. Each dict should contain:
            1. market_id (str): The market ID
            2. rationale (str): Explanation for your decision and why you think this market is mispriced (or correctly priced if skipping). Write at least a few sentences. If you take a strong bet, make sure to highlight the facts you know/value that the market doesn't.
            3. odds (float, 0 to 1): The odds you think the market will settle at (your true probability estimate)
            4. confidence (int, 0 to 10): Your confidence in the odds and your bet. Should be between 0 (absolute uncertainty, you shouldn't bet if you're not confident) and 10 (absolute certainty, then you can bet high).
            5. bet (float, -1 to 1): The amount in dollars that you bet on this market (can be negative if you want to buy the opposite of the market)
        unallocated_capital (float): Fraction of capital not allocated to any bet (0.0 to 1.0)
    """
    # Manual type checks for market_decisions
    if not isinstance(market_decisions, list):
        raise TypeError(
            f"market_decisions must be a list, got {type(market_decisions).__name__}"
        )

    if not market_decisions or len(market_decisions) == 0:
        raise ValueError(
            "No market decisions provided - at least one market decision is required"
        )

    for i, decision in enumerate(market_decisions):
        if not isinstance(decision, dict):
            raise TypeError(
                f"market_decisions[{i}] must be a dict, got {type(decision).__name__}"
            )

    # Manual type checks for unallocated_capital
    if not isinstance(unallocated_capital, (int, float)):
        raise TypeError(
            f"unallocated_capital must be a float or int, got {type(unallocated_capital).__name__}"
        )

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
        try:
            assert int(decision_dict["confidence"]) == float(
                decision_dict["confidence"]
            )
            decision_dict["confidence"] = int(decision_dict["confidence"])
            assert 0 <= decision_dict["confidence"] <= 10
        except Exception:
            raise TypeError(
                f"Your confidence must be between an integer 0 and 10, got {decision_dict['confidence']} for market {decision_dict['market_id']}"
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


class ListMarketInvestmentDecisions(BaseModel):
    market_investment_decisions: list[MarketInvestmentDecision]
    unallocated_capital: float


class CompleteMarketInvestmentDecisions(ListMarketInvestmentDecisions):
    full_response: Any
    token_usage: TokenUsage | None = None
    sources_google: list[str] | None = None
    sources_visit_webpage: list[str] | None = None

def _should_retry(exception: Exception) -> bool:
    """Check if the exception is a rate limit error."""
    error_str = str(exception).lower()
    return (
        "BadRequest".lower() in error_str
        or "Bad Request".lower() in error_str
        or "ValidationError".lower() in error_str
        or "ContextError".lower() in error_str
        or "maximum context length".lower() in error_str
        or "context window".lower() in error_str
    )


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception(_should_retry),
    before_sleep=before_sleep_log(logger, logging.ERROR),
    after=after_log(logger, logging.ERROR),
    reraise=False,
)
def run_smolagents(
    model_info: ModelInfo,
    question: str,
    cutoff_date: date | None,
    search_provider: Literal["serpapi", "bright_data", "serper"],
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

    google_search_tool = GoogleSearchTool(
        provider=search_provider, cutoff_date=cutoff_date
    )
    visit_webpage_tool = VisitWebpageToolSaveSources()
    tools = [
        google_search_tool,
        visit_webpage_tool,
        final_answer,
    ]
    if model_info.agent_type == "code":
        agent = CodeAgent(
            tools=tools,
            model=model_client,
            max_steps=max_steps,
            return_full_result=True,
            additional_authorized_imports=["requests"],
        )
    else:  # toolcalling is default
        agent = ToolCallingAgent(
            tools=tools,
            model=model_client,
            max_steps=max_steps,
            return_full_result=True,
        )

    full_result = agent.run(prompt)
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=full_result.output[0],
        unallocated_capital=full_result.output[1],
        full_response=full_result.steps,
        token_usage=full_result.token_usage,
        sources_google=google_search_tool.sources if google_search_tool.sources else None,
        sources_visit_webpage=visit_webpage_tool.sources if visit_webpage_tool.sources else None,
    )


def _get_cached_research_result(model_info: ModelInfo, target_date: date, event_id: str) -> str | None:
    """Try to load cached research result from storage."""
    if model_info is None or target_date is None or event_id is None:
        return None
        
    model_result_path = model_info.get_model_result_path(target_date)
    cache_file_path = model_result_path / f"{event_id}_full_result.txt"
    
    if file_exists_in_storage(cache_file_path):
        logger.info(f"Loading cached research result from {cache_file_path}")
        return read_from_storage(cache_file_path)
        
    return None

def _save_research_result_to_cache(
    research_output: str, model_info: ModelInfo, target_date: date, event_id: str
) -> None:
    """Save research result to cache storage."""
    if model_info is None or target_date is None or event_id is None:
        return
        
    model_result_path = model_info.get_model_result_path(target_date)
    cache_file_path = model_result_path / f"{event_id}_full_result.txt"
    
    write_to_storage(cache_file_path, research_output)
    logger.info(f"Saved research result to cache: {cache_file_path}")


def structure_final_answer(
    research_output: str,
    original_question: str,
    structured_output_model_id: str = "huggingface/fireworks-ai/Qwen/Qwen3-Coder-30B-A3B-Instruct",
) -> tuple[list[MarketInvestmentDecision], float]:
    structured_model = LiteLLMModel(model_id=structured_output_model_id)

    structured_prompt = textwrap.dedent(f"""
        Based on the following research output, extract the investment decisions for each market:
        


        **ORIGINAL QUESTION AND MARKET CONTEXT:**
        <original_question>
        {original_question}
        </original_question>

        **RESEARCH ANALYSIS OUTPUT:**
        <research_output>
        {research_output}
        </research_output>
                
        Your output should be list of market decisions. Each decision should include:


        {BET_DESCRIPTION}

        Make sure to directly use elements from the research output: return each market decision exactly as is, do not add or change any element, extract everything as-is.

        **OUTPUT FORMAT:**
        Provide a JSON object with:
        - "market_investment_decisions": Array of market decisions
        - "unallocated_capital": Float (0.0 to 1.0) for capital not allocated to any market

        **VALIDATION:**
        - All market IDs must match those in the original question's "AVAILABLE MARKETS" section
        - Sum of absolute bet values + unallocated_capital should equal 1.0
        - All rationales should reflect insights from the research analysis
        - Confidence levels should reflect the certainty of your analysis
        - If no good betting opportunities exist, you may return an empty market_investment_decisions array and set unallocated_capital to 1.0
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
        float(unallocated_capital),
    )


def run_openai_deep_research(
    model_id: str,
    question: str,
    model_info: ModelInfo | None = None,
    target_date: date | None = None,
    event_id: str | None = None,
) -> CompleteMarketInvestmentDecisions:
    # Try to load cached result first
    cached_result = _get_cached_research_result(model_info, target_date, event_id)
    if cached_result is not None:
        research_output = cached_result
        full_response = None  # We don't have the full response when loading from cache
    else:
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
        
        # Save to cache before attempting structured output
        _save_research_result_to_cache(research_output, model_info, target_date, event_id)

    # Use structured output to get EventDecisions
    structured_market_decisions, unallocated_capital = structure_final_answer(
        research_output, question
    )
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=structured_market_decisions,
        unallocated_capital=unallocated_capital,
        full_response=full_response.model_dump() if full_response is not None else None,
        token_usage=TokenUsage(
            input_tokens=full_response.usage.input_tokens,
            output_tokens=full_response.usage.output_tokens
            + full_response.usage.output_tokens_details.reasoning_tokens,
        ) if full_response is not None else None,
    )


def run_perplexity_deep_research(
    model_id: str,
    question: str,
    model_info: ModelInfo | None = None,
    target_date: date | None = None,
    event_id: str | None = None,
) -> CompleteMarketInvestmentDecisions:
    # Try to load cached result first
    cached_result = _get_cached_research_result(model_info, target_date, event_id)
    if cached_result is not None:
        research_output = cached_result
        full_response = None  # We don't have the full response when loading from cache
    else:
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
        
        # Save to cache before attempting structured output
        _save_research_result_to_cache(research_output, model_info, target_date, event_id)

    structured_market_decisions, unallocated_capital = structure_final_answer(
        research_output, question
    )
    return CompleteMarketInvestmentDecisions(
        market_investment_decisions=structured_market_decisions,
        unallocated_capital=unallocated_capital,
        full_response=full_response,
        token_usage=TokenUsage(
            input_tokens=full_response["usage"]["prompt_tokens"],
            output_tokens=full_response["usage"]["completion_tokens"],
        ) if full_response is not None else None,
    )
