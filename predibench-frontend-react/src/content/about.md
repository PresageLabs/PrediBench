## PrediBench: Testing AI models on prediction markets

AI models shine on within-distribution tasks, thus cracking standardized math or medicine exams ; but what about predicting the future, the realm of out-of-distribution events ?

We decided to put test this forecasting ability: **Every day, we let AI models bet 1$ on top events from [Polymarket](https://polymarket.com/).**

Tracking the profits on different metrics then yields PrediBench, and the above leaderboard.

- By nature, benchmark **cannot be overfitted**: since the test events are real-time prediction markets following real-world events, there’s no chance that models have seen the test set in training.
- It is also **generalist**, since the questions picked from Polymarket cover a wide range of newsworthy topic, from economics to pop culture.

We publish the entirety of this work in open source: code, data, experiments, to let the community iterate on it.

## Motivation

Prediction is a difficult science. We believe that in the future, AI models are poised to possess a superhuman ability to predict the future.

Why could that be? Because the ingredients of foresight are on the way to being mastered by AI models.

Amongst the example of striking prediction ability shown by individuals in history, what these individuals had in common was a combination of profound knowledge and of well-applied, bold judgement (one could define "judgement" as a combination of critical thinking, probabilistic reasoning, and causality understanding). (NOTE: forward-thinking?)

In 1919, French historian Jacques Bainville predicted that the Treaty of Versailles that had just closed the World war, would have dire consequences[^consequences_politiques]. Far from the optimism of his contemporaneous at the time, he announced an upcoming war. He foretold that a powerful and revengeful social republic of Germany would raise again to power. That it would annex Austria, and the Sudeten german-speaking minorities. He predicted the alliance of Russia and Germany, their siding together against Poland. He warned of the alliance of Italy.

When the Second World War broke out, two decades later, the first years followed the exact steps he had predicted.

> Bainville’s stunning prescience was not a product of chance: it was a mechanical application of his immense knowledge of European geopolitics and of his bold judgement, that defied the views of his time.

Knowledge allowed him to draw from history a myriad of situations similar to his present, where each situation's unfolding provided heuristics that could apply again. His good judgement then allowed to weigh and combine these different historical heuristics to assess the probability distribution of different outcomes in the future. 

**Knowledge provides the building blocks, judgement assembles them.** On both knowlege and judgement, recent progress has been massive for AI models:

- **Knowledge:** Leading models already know more in most areas of science than PhD students specialized in these areas [^GPQA]. These models possess a knowledge of both superhuman breadth and depth.
- **Judgement:** models have historically been struggling with causality and critical thinking, but recent progress has brought them nearly up to human skill[^gold_IMO].

Thus we expect AI models to become good forecasters: we built PrediBench to put this intuition to the test.

## Methods

- Agents Framework: All models ran under a **shared [smolagents](https://github.com/huggingface/smolagents) setup**. We defaulted to **CodeAgent** but switched to **ToolCallingAgent** when it reduced errors. In practice: **OpenAI** and **DeepSeek** models worked best with ToolCalling, while **Gemini** models were stronger with CodeAgent. **DeepResearch models** used their own native framework. 

This hybrid setup let us maximize performance across models while keeping the evaluation pipeline consistent.

Then on regular decision dates (thrice per week for the first month), each model is provided with a list of featured events on which to place bets.

- Event Choice Strategy : We focus on the **top 10 trending Polymarket events**, ranked by one-week trading volume.
    - To avoid stagnant bets, we only pick markets that **end within two months**.
    - By rotating through fast-moving, high-attention markets, our leaderboard stays dynamic and captures the **real pulse of prediction markets**.
    - We also **exclude crypto events**, since their high volatility goes against our goal of testing reasoning from fundamentals.

The agent run can go as follows:

You can follow a real example of agent run [at this link](https://predibench.com/decision/gpt-5/42659/2025-09-17).

Each market has two mutually exclusive, discrete outcomes. An overwhelming majority of outcome couples are "Yes vs No", exceptions being for instance the two opponents of a sports match. Let us place ourselves in the “Yes vs No” alternative.

Placing a negative bet means that the agents bet the sum of money on the negative outcome. Some bets can have outsized returns : for instance, if the “Yes” on an event is priced at 91% and the agent bets against the market, effectively buying the same amount of “no shares”, the upside is huge : for instance, the “Yes” market price dropping to 73% would triple the stake.

### Metrics

We evaluate models over several metrics, emphasizing different aspect of investment choices:

- **Average returns** measures profitability: each bet’s return is computed over several time horizons : how much did this bet return after 1 day, 2 days, 7 days ? These returns are averaged over all events to yield an average return per model, per each time horizon
- **Brier Score** measures probability estimates: upon generating their betting decision, models are prompted to also provide a probability estimate of the “Yes” outcome. This can be used to compute the cost function of error against the realised outcome : the Mean Squared Error between estimated probabilities and actual outcome is called the Brier Score. Possible scores range from 0 (best) to 1 (worst).
- **Annualised Sharpe** measures volatility risk: when using AI models for financial choices, the volatility of returns is an important aspect. The [Sharpe ratio](https://en.wikipedia.org/wiki/Sharpe_ratio) allows to downweigh the average of a series of returns by its volatility, thus factoring in a measure of the risk taken by undergoing the investment. In our case, we calculate the Sharpe ratio for different holding horizons : 1 day, 2 days, 7 days. We annualize it to represent what these strategies would represent over an entire year.

> Word of caution: Although these performance metrics are calculated on real market prices, they eschew some important parts of an investment pipeline, such as the bid-ask sprea, for ths sake of simplicity. This pipeline would certainly not be viable in its current state under real investment conditions.

## Results

### Outcome

- Models vs Market baseline on all criteria

{caption="Return Ranking", path=model_performance_comprehensive_analysis/average_return_ranking.json, second_path=model_performance_comprehensive_analysis/average_return_ranking.json}

## Experiments

### Market behaviour

News can have a sudden and massive impact on prediction markets, like when the news of [Zohran Mahmadi winning the Democratic primary](https://x.com/GlobeEyeNews/status/1937760643261825210) elicited a 40% change of the rate for his election over less than one hour.

{caption="On June 25, 2025, the market for Zohran mahmadi becoming Mayor of NYC jumped up - but the transition took one full hour." path="sudden_price_change/nyc_election_mahmadi.json"}

Given this potentially strong effect of news, we expect the information to decay quite quickly through time, leading us to limit the holding period of bets to at most 7 days.

### Model Performance


Models provide both probability estimates and corresponding bet amounts for each market. This analysis compares the performance of original model bet amounts versus Kelly criterion-optimized amounts, which theoretically maximize expected growth based on probability estimates and available capital.

{caption="Kelly vs Original Betting Strategy - Comparison of 7-day returns using original bet amounts versus Kelly criterion-derived amounts", path="market_dynamics/bet_strategy_comparison.json"}

Interestingly, most models outperformed Kelly criterion optimization when using their original bet amounts, suggesting that models incorporate risk management considerations beyond pure mathematical optimization (notable exceptions include the DeepSeek family and Gemini Pro, where the application of Kelly optimization improved predictions).

In other words **models are good at predicting, they are also good at betting**.

### Model Consistency

#### Model Decision Distribution Analysis

To understand how different models make betting decisions, we analyzed the distribution of model choices across 32 runs to predict the ![Federal Reserve interest rates](https://polymarket.com/event/fed-decision-in-october?tid=1758495631699), for the models Qwen3-Coder-480B and GPT-OSS-120B. This analysis reveals the consistency and strategy patterns of each model.

{caption="Fed Event: Model Comparison - Distribution of estimated probabilities, bet amounts, and confidence levels across models", path="32_run_results_FED/fed_readable_comparative.json"}

The probability distribution reveals significant uncertainty in model predictions, with wide variance around market prices. This uncertainty translates into conservative betting behavior, explaining why the bet amount distribution median approaches zero - models hedge against their own uncertainty by making smaller bets.


### Importance of in-depth research

Our agents were given two tools: a general GoogleSearch that returns a list of links and their snippet texts, and a VisitWebpage tool to visit individual webpages.
One could expect an analyst to increase performance when double-checking sources using VisitWebpage : but often, models did not verify sources, as long as they had elements of answer in the google search snippets. 

It appears that double-checking results increases research quality. Returns grows with the count of webpages visited - Perplexity’s Sonar-Deep-Research is not shown on this graph, visited over 16 webpages on average - which also reinforces the hypothesis that visiting more sources leads to success.

{caption="Performance seems correlated with the count of pages visited" path="sources_vs_performance_analysis/webpage_sources_vs_returns.json"}


### Predicted odds

A basic ability of models should be to provide consistent bet and probability estimates - if the model estimates an event to be more probable (resp. less) than the market prices it, it should place its bet on the Yes (resp. No).

To measure this we measure the criterion of **bet-edge consistency**. When noting "edge" the difference of model's estimated probability minus the market prices, the bet is considered consistent if:
- **No bet is placed**: the model can always decide to place no bet.
- **A bet is placed**: then if the edge is positive, we expect the bet to be positive, and if the edge is negative.

We find that this bet-edge consistency correlates well with the general strength of models.

{caption="Bet-Edge Consistency by Model - Models with higher consistency rates between their betting decisions and estimated market edge tend to perform better", path="market_dynamics/consistency_rates.json"}

## Next steps

- Each [model decision](https://predibench.com/decision/gpt-5/42659/2025-09-17) can be commented via [giscus](https://giscus.app/), and the comments will appear directly under the repo's [discussions page](https://github.com/clairvoyance-tech/PrediBench/discussions): we invite you to hop in and provide feedback!
- Do contact us about anything : contact form.

In the next months, we plan to push the boundary of AI models prediction capabilities: we are starting [Clairvoyance AI](https://clairvoyance-ai.co).

## Citation

```bibtex
@Misc{predibench,
  title =        {PrediBench: a live benchmark to measure LLM's ability to predict the future},
  author =       {Charles Azam and Aymeric Roucher},
  howpublished = {\url{https://github.com/clairvoyance-tech/PrediBench}},
  year =         {2025}
}
```

## Bibliography

[^consequences_politiques]: Bainville, J. (1919). Les conséquences politiques de la paix. [Full text here.](https://classiques.uqam.ca/classiques/bainville_jacques/consequences_pol_paix/consequences_pol_paix.pdf)


[^GPQA]: Rein, D., Hou, B. L., Stickland, A. C., Petty, J., Pang, R. Y., Dirani, J., Michael, J., & Bowman, S. R. (2023). GPQA : A Graduate-Level Google-Proof Q&A Benchmark (No. arXiv:2311.12022). arXiv. https://doi.org/10.48550/arXiv.2311.12022

[^gold_IMO]: The recent progresses in math exemplifies this vast improvement of causal thinking: [Gemini with Deep Think achieves gold-medal standard at the International Mathematical Olympiad](https://deepmind.google/discover/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/)