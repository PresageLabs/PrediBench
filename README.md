# PrediBench: Testing AI models on prediction markets


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/Website-Live-green)](https://predibench.com)
[![GitHub Discussions](https://img.shields.io/github/discussions/clairvoyance-tech/PrediBench)](https://github.com/clairvoyance-tech/PrediBench/discussions)

> **A live benchmark that tests AI models' ability to predict real-world events through prediction markets**

AI models shine on within-distribution tasks, thus cracking standardized math or medicine exams; but what about predicting the future, the realm of out-of-distribution events?

We decided to put test this forecasting ability: **Every day, we let AI models bet $1 on top events from [Polymarket](https://polymarket.com/).**

## Live Leaderboard

Check out the [**Live Leaderboard**](https://predibench.com) to see how AI models perform in real-time!

## Key Features

- ** Cannot be overfitted**: Test events are real-time prediction markets following real-world events
- ** Generalist benchmark**: Questions from Polymarket cover economics, politics, sports, pop culture, and more
- ** Tests agentic capabilities**: Models perform series of tool calls (web search, page visits) to make informed decisions
- ** Multiple metrics**: Average returns, Brier scores, Sharpe ratios
- ** Fully open source**: All code, data, and experiments available for community iteration

## Repository Structure

```
market-bench/
├── predibench-core/          # Core prediction engine
│   ├── src/predibench/       # Main Python package
│   ├── scripts/              # Automation scripts
│   └── tests/                # Unit tests
│
├── predibench-backend/       # FastAPI backend service
│   └── main.py              # API endpoints
│
├── predibench-frontend-react/ # React web application
│   ├── src/                  # Frontend source code
│   ├── public/               # Static assets
│   └── package.json          # Node dependencies
```

## Quick Start

### Prerequisites
- Node.js 20+ and npm/yarn
- Python 3.11+ (for running experiments) with uv

### Installation

```bash
# Clone the repository
git clone https://github.com/PresageLabs/PrediBench.git
cd PrediBench

# Install python
cd predibench-core
uv sync

# Install frontend dependencies
cd predibench-frontend-react
npm install

# Run the development server
npm run dev

# Run the backend development server
cd predibench-backend
uvicorn main:app --reload --port 8080 
```

### Running Experiments

```bash
# Install python
cd predibench-core
uv sync

# Run benchmark experiments
python ./scripts/run_investments.py --provider huggingface-qwen
```

## Motivation

Prediction is a difficult science. We believe that in the future, AI models are poised to possess a superhuman ability to predict the future.

Why could that be? Because the main ingredients of foresight are on the way to being mastered by AI models.

Amongst the authors of outstandingly precise predictions throughout history, the shared characteristic was a combination of **profound knowledge** and of **clear judgement** (one could define "judgement" as a combination of critical thinking, probabilistic reasoning, and causality understanding).

In 1919, French historian Jacques Bainville made a spectacular display of these two characteristics when he predicted the first years of WW2, 20 years in advance.

Reflecting on the Treaty of Versailles that had just closed the World war, he went against the optimism of the zeitgeist, to instead announce the coming of a new war[^consequences_politiques]. He foretold that a powerful and revengeful social republic of Germany would raise again to power. That it would annex Austria, and the Sudeten german-speaking minorities. He predicted the alliance of Russia and Germany, their siding together against Poland. He announced that the alliance of Italy would shift in favor of Germany.

When the Second World War broke out, two decades later, it started in the exact steps that Bainville had predicted.

> Bainville's stunning prescience was not a product of chance: it was a mechanical application of his immense knowledge of European geopolitics, articulated through sound judgement.

Knowledge allowed him to draw from history a myriad of events with similar aspects to his present, providing heuristics that could apply again. His good judgement then allowed to weigh and combine these historical heuristics to assess the probability distribution of different outcomes in the future, thus providing a response that defied the views of his time.

**Knowledge provides the building blocks, judgement assembles them.** On both knowlege and judgement, recent progress has been massive for AI models:

- **Knowledge:** Leading models already know more in most areas of science than PhD students specialized in these areas [^GPQA]. These models possess a knowledge of both superhuman breadth and depth.
- **Judgement:** models have historically been struggling with causality and critical thinking, but recent progress has brought them nearly up to human skill[^gold_IMO].

Thus we expect AI models to become good forecasters: we built PrediBench to put this intuition to the test.

## Methods

### News and Prediction markets

We let LLMs place bets on prediction markets from [Polymarket](https://polymarket.com/).

Each market has two mutually exclusive, discrete outcomes. An overwhelming majority of outcome couples are "Yes vs No", exceptions being for instance the two opponents of a sports match. Let us place ourselves in the "Yes vs No" alternative.

Placing a negative bet means to bet the sum of money on the negative outcome. Some bets can have outsized returns : for instance, if the "Yes" on an event is priced at 91% and the bet has been placed against the market, effectively buying the same amount of "no shares", the upside is huge : for instance, the "Yes" market price dropping to 73% would triple the stake.

News can have a sudden and massive impact on prediction markets, like when the news of [Zohran Mahmadi winning the Democratic primary](https://x.com/GlobeEyeNews/status/1937760643261825210) elicited a 40% change of the rate for his election over less than one hour.

![Zohran Market Movement](readme_graphs/zohran_market.png)
*On June 25, 2025, the market for Zohran Mahmadi becoming Mayor of NYC jumped up - but the transition took one full hour.*

Given this potentially strong effect of news, we expect the information to decay quite quickly through time, leading us to limit the holding period of bets to at most 7 days.

### Investment process


The investment pipeline runs for all models on regular decision dates (thrice per week for the first month). It goes as follows:

1. Seletion of 10 events
- Event Choice Strategy : We focus on the **top 10 trending Polymarket events**, ranked by one-week trading volume.
    - To avoid stagnant bets, we only pick markets that **end within two months**.
    - By rotating through fast-moving, high-attention markets, our leaderboard stays dynamic and captures the **real pulse of prediction markets**.
    - We also **exclude crypto events**, since their high volatility goes against our goal of testing reasoning from fundamentals.

2. Each model places $1 on each of the 10 events.
- Each model is running with an agent Framework: All models ran under a **shared [smolagents](https://github.com/huggingface/smolagents) setup**. We defaulted to **CodeAgent** but switched to **ToolCallingAgent** when it reduced errors. In practice: **OpenAI** and **DeepSeek** models worked best with ToolCalling, while **Gemini** models were stronger with CodeAgent. **DeepResearch models** used their own native framework. This hybrid setup let us maximize performance across models while keeping the evaluation pipeline consistent.
- Importantly the model is asked to provide for each market the following:
```python
class SingleInvestmentDecision:
    rationale: str  # Explanation for your decision and why you think this market is mispriced (or correctly priced if skipping).
    estimated_probability: float # Betwen 0 and 1, Your estimate for the true probability of the market
    bet: float # The amount in dollars that you bet on this market (can be negative to buy the opposite of the market)
    confidence: int = # Your confidence in the estimated_probability and your bet. 0 for absolute uncertainty, 10 for absolute certainty
```
- If the model does not allocate the totality of the $1, the remainder is left unallocated.

3. Each investment is kept for a fixed period: the variables tracked are both its returns, and the gap between the `estimated_probability` and the real event outcome.


### How an Agent Runs

The agents are built with **[smolagents](https://github.com/huggingface/smolagents)**, and they are provided with two tools:

- **`web_search`**: Performs Google searches to gather current information about events, candidates, and market trends
- **`visit_webpage`**: Retrieves and analyzes specific web pages for detailed information, official statements, and primary sources
- **`final_answer`**: Returns a structured JSON output with betting decisions, including market IDs, rationale, odds estimates, confidence levels, and bet amounts

Each agent must allocate exactly $1 across all markets, with positive bets indicating "Yes" positions and negative bets indicating "No" positions. The `unallocated_capital` represents funds kept in reserve for risk management. The final structured output ensures consistent, machine-readable decisions that can be tracked and evaluated over time.


Here's how **Grok-4** analyzed the [2025 Nobel Peace Prize](https://predibench.com/decision/grok-4-0709/31406/2025-09-17?source=event&decisionDatetime=2025-09-17T07%3A01%3A22.460814&modelName=Grok+4&eventTitle=Nobel+Peace+Prize+Winner+2025) prediction market on September 17, 2025:

<details>
<summary><b>Click to see example: How Grok-4 analyzed the Nobel Peace Prize market</b></summary>

::step:: Step 1 - Initial Market Research
timing: 40.6s
tokens: ↗ 10.6K ↘ 95
model: I need to allocate $1.0 across these Nobel Peace Prize markets by estimating true probabilities and betting where markets seem mispriced. First, I'll research current predictions and odds for the 2025 Nobel Peace Prize.
tool: web_search
args: query: "2025 Nobel Peace Prize favorites odds predictions September 2025"
output: Search Results:
• Nobel Peace Prize Odds & Prediction 2025: Trump Among...
• Oddspedia: Trump 2nd Favorite at +300
• Multiple betting sites showing varied odds for candidates
• Sudan's Emergency Response Rooms emerging as a contender

::step:: Step 2 - Checking September Updates
timing: 36.7s
tokens: ↗ 11.7K ↘ 144
model: The previous search results are from August 2025, but market data goes up to September 17. Prices have shifted significantly (e.g., Trump dropped from ~0.095 to 0.043, Sudan's ERR surged). Let me find more recent predictions.
tool: web_search
args: query: "Nobel Peace Prize 2025 predictions as of September 2025"
output: Updated Results:
• Trump at +300 odds (about 25% implied probability)
• Discrepancies between betting sites and Polymarket
• Sudan's Emergency Response Rooms gaining momentum
• 338 nominees total, announcement date: October 10, 2025

::step:: Step 3 - Visiting Detailed Predictions
timing: 25.0s
tokens: ↗ 12.6K ↘ 163
model: The search results indicate discrepancies in odds across sources. For instance, one source has Trump at +300 (about 25%), but Polymarket has him at 4.3%. This could mean Polymarket has newer information. Let me check specific prediction sites.
tool: visit_webpage
args: url: "https://oddspedia.com/insights/features/nobel-peace-prize-odds-and-predictions"
output: Nobel Peace Prize Odds 2025 | Trump 2nd Favorite at +300
• Updated odds from major bookmakers
• Sudan's Emergency Response Rooms highlighted
• Yulia Navalnaya among top candidates
• Analysis of committee preferences for humanitarian work

::step:: Step 4 - Expert Analysis (PRIO)
timing: 19.4s
tokens: ↗ 16.8K ↘ 96
model: The PRIO shortlist is a reliable source for expert predictions on Nobel Peace Prize winners. They release it annually around September, based on research. This should give me a solid basis for my betting decisions.
tool: web_search
args: query: "PRIO Nobel Peace Prize shortlist 2025"
output: PRIO Director's List Results:
• Sudan's Emergency Response Rooms - TOP PICK
• International Court of Justice
• International Criminal Court
• Various humanitarian organizations
• Note: Yulia Navalnaya NOT on PRIO shortlist

::step:: Step 5 (Truncated) - Final Decision
timing: [Total: 324.7s]
tokens: [Total: ↗ 134.3K ↘ 2.6K]
model: Based on PRIO's expert analysis (which has strong predictive history), Sudan's ERR at 17.5% is undervalued. They're the top pick on PRIO's shortlist. I'll allocate my bets across 7 markets based on this analysis.
tool: final_answer
args: market_decisions=[7 market decisions], unallocated_capital=0.05
output: FINAL STRUCTURED OUTPUT:
{
  "market_investment_decisions": [
    {
      "market_id": "560873",
      "rationale": "Sudan's Emergency Response Rooms is the top pick on the PRIO Director's shortlist for 2025, which has a strong history of predicting winners or themes (e.g., correctly shortlisting Nihon Hidankyo in 2024). Their work providing aid in Sudan's humanitarian crisis fits the committee's preference for timely, grassroots peace efforts amid conflict, similar to past laureates like MSF in 1999. The market price of 0.175 underestimates this, possibly because it's reacting to recent news but not fully accounting for PRIO's expert endorsement and the committee's pattern of awarding humanitarians in crisis years. I value the PRIO analysis highly, as it's based on deep research into nominations and committee trends, which the market seems to overlook in favor of earlier favorites.",
      "odds": 0.30,
      "confidence": 8,
      "bet": 0.40
    },
    {
      "market_id": "560870",
      "rationale": "Yulia Navalnaya was an early betting favorite in August due to her opposition work following Navalny's death, but she's absent from the PRIO shortlist, which prioritizes humanitarian and institutional efforts over individual dissidents this year. Recent news in September shows no momentum-building events for her, and the committee often avoids highly politicized Russian figures amid ongoing war. The market at 0.07 overprices her chances, lagging behind the shift toward groups like ERR; I see her true odds lower based on PRIO's omission and historical patterns where dissidents win only in specific contexts (e.g., Sakharov in 1975).",
      "odds": 0.04,
      "confidence": 6,
      "bet": -0.15
    },
    {
      "market_id": "560864",
      "rationale": "UNRWA has faced significant controversies in 2025, including funding cuts and allegations of staff involvement in attacks, which have damaged its reputation despite its Gaza aid work. It's not on the PRIO shortlist, which favors less controversial humanitarians like ERR or courts like ICJ/ICC. The market price of 0.065 overestimates, possibly due to name recognition, but ignores these scandals and the committee's avoidance of divisive orgs (e.g., no award to similar groups recently). My lower estimate reflects recent negative press not fully priced in.",
      "odds": 0.02,
      "confidence": 5,
      "bet": -0.10
    },
    {
      "market_id": "560874",
      "rationale": "Doctors Without Borders is a perennial strong candidate for humanitarian work, but it's not highlighted on the PRIO list this year, which tops with ERR for Sudan aid—a more acute, current crisis. MSF won in 1999, and repeats are rare; the market at 0.055 slightly overprices it relative to ERR's momentum. I think the market is anchoring on general reputation without accounting for PRIO's specific focus on Sudan, leading to a mispricing.",
      "odds": 0.03,
      "confidence": 5,
      "bet": -0.10
    },
    {
      "market_id": "560856",
      "rationale": "Donald Trump has multiple nominations and recent news buzz from leaders like Netanyahu, but he's not on the PRIO shortlist, which avoids polarizing political figures without concrete peace achievements (e.g., no US presidents since Obama in 2009). His odds dropped in September likely due to election dynamics, but at 0.043, the market still overvalues name recognition over the committee's preference for non-partisan efforts. My estimate is lower, factoring in PRIO's focus on apolitical humanitarians.",
      "odds": 0.03,
      "confidence": 7,
      "bet": -0.10
    },
    {
      "market_id": "560867",
      "rationale": "Alexei Gorinov is a Russian dissident imprisoned for anti-war statements, but like Navalnaya, he's not on PRIO's list, which emphasizes global institutions and aid over individual activists this year. The price of 0.021 overestimates, possibly due to sympathy for Russian opposition, but the committee rarely awards multiple in similar categories closely (e.g., post-Navalny focus shifted). My lower odds reflect this thematic mismatch.",
      "odds": 0.01,
      "confidence": 4,
      "bet": -0.05
    },
    {
      "market_id": "560868",
      "rationale": "María Corina Machado is a key Venezuelan opposition leader amid political turmoil, but she's not on PRIO's shortlist, which prioritizes broader peace institutions. The market at 0.0115 is slightly high given competition from top picks like ERR; recent news hasn't elevated her globally. I see minor overpricing due to regional interest not translating to Nobel priority.",
      "odds": 0.01,
      "confidence": 4,
      "bet": -0.05
    }
  ],
  "unallocated_capital": 0.05,
  "summary": "Primary bet FOR Sudan's ERR (+$0.40), betting AGAINST multiple candidates: Navalnaya (-$0.15), UNRWA (-$0.10), MSF (-$0.10), Trump (-$0.10), Gorinov (-$0.05), Machado (-$0.05)."
}

</details>

You can explore more agent decisions with full logs [on our platform](https://predibench.com/events/20459).

### Metrics

We evaluate models over several metrics, emphasizing different aspect of investment choices:

- **Average returns** measures profitability: each bet's return is computed over several time horizons : how much did this bet return after 1 day, 2 days, 7 days ? These returns are averaged over all events to yield an average return per model, per each time horizon
- **Brier Score** measures probability estimates: upon generating their betting decision, models are prompted to also provide a probability estimate of the "Yes" outcome. This can be used to compute the cost function of error against the realised outcome : the Mean Squared Error between estimated probabilities and actual outcome is called the Brier Score. Possible scores range from 0 (best) to 1 (worst).
- **Annualised Sharpe** measures volatility risk: when using AI models for financial choices, the volatility of returns is an important aspect. The [Sharpe ratio](https://en.wikipedia.org/wiki/Sharpe_ratio) allows to downweigh the average of a series of returns by its volatility, thus factoring in a measure of the risk taken by undergoing the investment. In our case, we calculate the Sharpe ratio for different holding horizons : 1 day, 2 days, 7 days. We annualize it to represent what these strategies would represent over an entire year.

> Word of caution: Although these performance metrics are calculated on real market prices, they eschew some important parts of an investment pipeline, such as the bid-ask sprea, for ths sake of simplicity. This pipeline would certainly not be viable in its current state under real investment conditions.



### Baselines

Two baselines are added to the set:
- **Random baseline** picks a probability and a bet amount at random.
- **Market baseline** selects on each market the market price for its probability estimate, and always bets in the direction of the most favoured outcome.

## Results

Let us compare our models and the baselines:

![Average Returns per Model](readme_graphs/average_returns_per_model.png)
*Average returns over 7-day holding period*

![Brier Score per Model](readme_graphs/brier_score_per_model.png)
*Brier Score - lower is better (measures probability calibration accuracy)*

- While most models tested are not profitable, half of them beat the market baseline. And the most recent/powerful ones draw a profit.

This shows that AI models are becoming better at forecasting!

### Predictive ability correlates well with general performance

Average returns and Brier score tend to correlate well with general performance, which we can visualize by comparing Brier scores to model scores on LMSys Arena[^arena].

![Brier Score vs LMSys Arena Score](readme_graphs/lmsys_arena_score.png)
*Brier Score correlates strongly with LMSys Arena performance*


### Research depth: counting visits

Our agents were given two tools: a general GoogleSearch that returns a list of links and their snippet texts, and a VisitWebpage tool to visit individual webpages.
One could expect an analyst to increase performance when double-checking sources using VisitWebpage : but often, models did not verify sources, as long as they had elements of answer in the google search snippets.

It appears that double-checking results increases research quality. Returns grows with the count of webpages visited - Perplexity's Sonar-Deep-Research is not shown on this graph, visited over 16 webpages on average - which also reinforces the hypothesis that visiting more sources leads to success.

![Mean Visited Webpages vs Performance](readme_graphs/mean_visited_webpages.png)
*Performance increases with the number of webpage visits during research*


## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Ways to Contribute

- **Provide feedback**: Comment on [model decisions](https://predibench.com/decision/gpt-5/42659/2025-09-17) via giscus
- **Report issues**: Open an issue on [GitHub](https://github.com/clairvoyance-tech/PrediBench/issues)
- **Submit PRs**: Improve the codebase, add features, or fix bugs
- **Share analysis**: Create notebooks analyzing model performance
- **Suggest markets**: Recommend interesting prediction markets to track

## Contact & Support

- **Website**: [predibench.com](https://predibench.com)
- **GitHub Discussions**: [Join the conversation](https://github.com/clairvoyance-tech/PrediBench/discussions)
- **Contact Form**: [Get in touch](https://predibench.com#contact)
- **Presage AI**: [presage-ai.com](https://presage-ai.com) - Our next venture in AI prediction capabilities

## Citation

```bibtex
@Misc{predibench,
  title =        {PrediBench: a live benchmark to measure LLM's ability to predict the future},
  author =       {Charles Azam and Aymeric Roucher},
  howpublished = {\url{https://github.com/PresageLabs/PrediBench}},
  year =         {2025}
}
```

## References

[^consequences_politiques]: Bainville, J. (1919). Les conséquences politiques de la paix. [Full text here.](https://classiques.uqam.ca/classiques/bainville_jacques/consequences_pol_paix/consequences_pol_paix.pdf)

[^GPQA]: Rein, D., Hou, B. L., Stickland, A. C., Petty, J., Pang, R. Y., Dirani, J., Michael, J., & Bowman, S. R. (2023). GPQA : A Graduate-Level Google-Proof Q&A Benchmark (No. arXiv:2311.12022). arXiv. https://doi.org/10.48550/arXiv.2311.12022

[^gold_IMO]: The recent progresses in math exemplifies this vast improvement of causal thinking: [Gemini with Deep Think achieves gold-medal standard at the International Mathematical Olympiad](https://deepmind.google/discover/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/)

[^arena]: Chiang, W.-L., Zheng, L., Sheng, Y., Angelopoulos, A. N., Li, T., Li, D., Zhang, H., Zhu, B., Jordan, M., Gonzalez, J. E., & Stoica, I. (2024). Chatbot Arena : An Open Platform for Evaluating LLMs by Human Preference (No. arXiv:2403.04132). arXiv. https://doi.org/10.48550/arXiv.2403.04132

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Polymarket](https://polymarket.com/) for providing real-time prediction markets
- [smolagents](https://github.com/huggingface/smolagents) for the agent framework
- All contributors and the open-source community

---

<p align="center">
  Made by <a href="https://presagelabs.com">Presage Labs</a>
</p>