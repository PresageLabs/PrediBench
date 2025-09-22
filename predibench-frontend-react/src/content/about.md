# About Page

***Can AI predict the future?***

AI models shine on within-distribution tasks, thus cracking standardized math or medicine exams ; but what about predicting the future, the realm of out-of-distribution events ?

We decided to put test this forecasting ability : this yields Predibench.

> Every day, we let AI models bet 1$ on some top Polymarket events.

Then, we can track the profit and additional metrics such as the Brier score.

This benchmark has the following advantages:

- **Cannot be overfitted**: Since the test events are real-time prediction markets following real-world events, there’s no chance that models have seen the test set in training.
- **Generalist:** the questions picked from Polymarket are very broad in nature, ranging from economics to celebrities.
- It evaluates LLMs in agentic mode : they can retrieve information from the Web.

We make this work entirely open source: code, data, experiments, to let the community iterate on it.

## Methods

- Agents Framework: All models ran under a **shared [smolagents](https://github.com/huggingface/smolagents) setup**. We defaulted to **CodeAgent** (multi-tool calls) but switched to **ToolCallingAgent** when it reduced errors. In practice: **OpenAI** (esp. GPT-5 Mini, GPT-OSS 120B) and **DeepSeek** models ****worked best with ToolCalling, while **Gemini** models were stronger with CodeAgent. **DeepResearch models** used their **own native framework** instead of ours. 
This hybrid setup let us maximize performance across models while keeping the evaluation pipeline consistent.

Then on regular decision dates (thrice per week for the first month), each model is provided with a list of featured events on which to place bets.

- Event Choice Strategy : We focus on the **top 10 trending Polymarket events**, ranked by one-week trading volume.
    - To keep things fresh, we only pick markets that **end within two months**, avoiding stagnant bets.
    - We also **exclude crypto events**: their extreme volatility goes against our goal of testing reasoning from fundamentals.
    - By rotating through fast-moving, high-attention markets, our leaderboard stays dynamic and captures the **real pulse of prediction markets**.

The agent run can go as follows:

You can follow a real example of agent run [at this link](https://predibench.com/decision/gpt-5/42659/2025-09-17).

Each market has two mutually exclusive, discrete outcomes : an overwhelming majority of outcome couples are Yes vs No, but sometimes it varies, such as two opponents of a sports match. Let us place ourselves in the “Yes vs No” choice.

Placing a negative bet means that the agents bet the sum of money on the negative outcome. Some bets can have outsized returns : for instance, if the “Yes” on an event is priced at 91% and the agent bets against the market, effectively buying the same amount of “no shares”, the upside is huge : for instance, the “Yes” market price dropping to 73% would triple the stake.

### Metrics

We evaluate models over several metrics, emphasizing different aspect of investment choices:

- **Average returns - profitability :** each bet’s return is computed over several time horizons : how much did this bet return after 1 day, 2 days, 7 days ? These returns are averaged over all events to yield an average return per model, per each time horizon
- **Brier Score - probability estimates:** upon generating their betting decision, models are prompted to also provide a probability estimate of the “Yes” outcome. This can be used to compute the cost function of error against the realised outcome : the Mean Squared Error between estimated probabilities and actual outcome is called the Brier Score : possible scores range from 0 (best) to 1 (worst).
- **Annualised Sharpe - volatility risk:** when using AI models for financial choices, the volatility of returns is an important aspect. The [Sharpe ratio](https://en.wikipedia.org/wiki/Sharpe_ratio) allows to downweigh the average of a series of returns by its volatility, thus factoring in a measure of the risk taken by undergoing the investment. In our case, we calculate the Sharpe ratio for different holding horizons : 1 day, 2 days, 7 days. More detail on Sharpe [here](https://www.reddit.com/r/quant/comments/pe7wyt/introducing_sharpe_ratios_why_investing_is_not/).

<aside>
⚠️
For the sake of simplicity, the average returns and annualized Sharpe are calculated on real market prices, but they eschew some important, complex parts of an investment pipeline: brokerage fees, bid-ask spread…
</aside>

## Results

### Outcome

- Models vs Market baseline on all criteria

{caption="Return Ranking", path=model_performance_comprehensive_analysis/average_return_ranking.json, second_path=model_performance_comprehensive_analysis/average_return_ranking.json}

## Experiments

### Market behaviour

News can suddenly change the price of some markets, like the news of [Zohran Mahmadi winning the Democratic primary](https://x.com/GlobeEyeNews/status/1937760643261825210) elicited a 40% change of the rate for his election over less than one hour.

{caption="On June 25, 2025, the market for Zohran mahmadi becoming Mayor of NYC jumped up - but the transition took one full hour." path="sudden_price_change/nyc_election_mahmadi.json"}

Since news can have such a strong effe

### Model Performance


Models provide both probability estimates and corresponding bet amounts for each market. This analysis compares the performance of original model bet amounts versus Kelly criterion-optimized amounts, which theoretically maximize expected growth based on probability estimates and available capital.

{caption="Kelly vs Original Betting Strategy - Comparison of 7-day returns using original bet amounts versus Kelly criterion-derived amounts", path="market_dynamics/bet_strategy_comparison.json"}

Interestingly, most models outperformed Kelly criterion optimization when using their original bet amounts, suggesting that models incorporate risk management considerations beyond pure mathematical optimization. Notable exceptions include the DeepSeek family and Gemini Pro, which benefited from Kelly optimization, indicating different internal betting strategies.

In other words **models are good at predicting, they are also good at betting**.

### Model Consistency

#### Model Decision Distribution Analysis

To understand how different models make betting decisions, we analyzed the distribution of model choices across 32 runs on ![Federal Reserve interest rate predictions](https://polymarket.com/event/fed-decision-in-october?tid=1758495631699) for the models Qwen3 Coder 480B and GPT-OSS 120B. This analysis reveals the consistency and strategy patterns of each model when faced with the same prediction markets.

{caption="Fed Event: Model Comparison - Distribution of estimated probabilities, bet amounts, and confidence levels across models", path="32_run_results_FED/fed_readable_comparative.json"}

The probability distribution reveals significant uncertainty in model predictions, with wide variance around market prices. This uncertainty translates into conservative betting behavior, explaining why the bet amount distribution median approaches zero - models hedge against their own uncertainty by making smaller bets.

#### Returns Analysis

The following analysis computes returns distribution after a week of market evolution. Despite the conservative betting approach, both models achieved positive mean returns, though with substantial variance reflecting the inherent uncertainty in prediction markets.

{caption="Fed Event: Returns Analysis - Profitability distribution and market-specific performance", path="32_run_results_FED/fed_returns_analysis.json"}


### Importance of retrieving sources

Average returns grows with the count of webpages visited - Perplexity’s Sonar-Deep-Research is not shown on this graph, visited over 16 webpages on average - which also reinforces the hypothesis that visiting more sources leads to success.

{caption="Performance seems correlated with the count of pages visited" path="sources_vs_performance_analysis/webpage_sources_vs_returns.json"}

### Predicted odds

Stronger models tend to produce probability estimates that align more closely with market odds — for example, GPT-5 vs. GPT-OSS 120B.

![image.png](About%20Page%2025e8d6bd102f80ce8f3be27e7ed42698/image%204.png)

![image.png](About%20Page%2025e8d6bd102f80ce8f3be27e7ed42698/image%205.png)

But does that translates to betting ? 

We looked into **bet-edge consistency**. A bet is considered consistent if:

- **No bet is placed** when the edge is below 5%.
- **A positive bet** is placed when the edge is above +5%.
- **A negative bet** is placed when the edge is below –5%.

We find that this bet-edge consistency correlates quite well with being a strong model.

{caption="Bet-Edge Consistency by Model - Models with higher consistency rates between their betting decisions and estimated market edge tend to perform better", path="market_dynamics/consistency_rates.json"}

And this translates into returns, the 7 day average return is correlated with the consistency rate.

{caption="Consistency vs Returns - Strong positive correlation between bet-edge consistency and 7-day average returns across models", path="market_dynamics/consistency_vs_7day_returns.json"}

## Next steps

Prediction is a difficult science. We believe that AI is on the way to becoming a superhuman forecaster.

History gives few examples of bright individuals predicting the future. What they had in common was a combination of profound knowledge and of good judgement.

In 1919, major French historian Jacques Bainville predicted that the Treaty of Versailles would have dire consequences. Far from the optimism of his contemporaneous, he announced an upcoming war : he announced that 20 years down the road, a powerful and revengeful Germany would first annex the Sudeten, then Austria, would then invade Poland before turning to France. That war broke out in 1939, exactly 20 years later, and it followed the exact steps predicted by Bainville.

Bainville’s prescience is stunning : but it was merely a mechanical application of his knowledge and judgement.

Knowledge is used to gather heuristics : from a priori data, cause A implies consequence B, and cause C implies consequence D.

Judgement, loosely defined as a combination of critical thinking, probabilistic reasoning, and causality understanding, then allows to weight the possible consequences and reliably assess the outcome’s probability distribution.

Knowledge and judgement : AI is already gathering these two ingredients.

- Knowledge : Leading models already know more in most areas of science than PhD students specialized in these areas. These models possess a knowledge of both superhuman breadth and depth.
- Judgement : models have historically been struggling with causality and critical thinking, but recent progress has brought them nearly up to human skill (SOURCE)

This benchmark, and the positive profits of the most advanced models, show that AI has now caught up with human level on predicting the future.

In the next months, we are going to push this boundary to a superhuman level. This is going to be called Clairvoyance.

![image.png](About%20Page%2025e8d6bd102f80ce8f3be27e7ed42698/image%208.png)

![image.png](About%20Page%2025e8d6bd102f80ce8f3be27e7ed42698/image%209.png)

![image.png](About%20Page%2025e8d6bd102f80ce8f3be27e7ed42698/image%2010.png)


### Citation

```bibtex
@Misc{predibench,
  title =        {PrediBench: a live benchmark to measure LLM's ability to predict the future},
  author =       {Charles Azam and Aymeric Roucher},
  howpublished = {\url{https://github.com/clairvoyance-tech/PrediBench}},
  year =         {2025}
}
```
