# PrediBench: AI-Powered Prediction Market Benchmark

**Can AI predict the future?** PrediBench is a live benchmark that measures LLM's ability to make real-world predictions by having AI models place daily $1 bets on top Polymarket events.

Visit the live leaderboard at [predibench.com](https://predibench.com)

## Overview

PrediBench evaluates AI models' forecasting abilities using real prediction markets, ensuring:
- **No overfitting**: Test events are real-time prediction markets following real-world events
- **Generalist evaluation**: Questions range from economics to celebrities
- **Agentic capabilities**: Models can retrieve and analyze web information

Every day, AI models bet on the top 10 trending Polymarket events, with performance tracked across multiple metrics.

## Key Features

### Benchmark Characteristics
- Daily automated predictions on top Polymarket events (by trading volume)
- Focus on events ending within 2 months
- Excludes crypto events to avoid extreme volatility
- Fully open-source: code, data, and experiments


### Evaluation Metrics
- **Average Returns**: Profitability across 1, 2, and 7-day horizons
- **Brier Score**: Accuracy of probability estimates (0=best, 1=worst)
- **Annualized Sharpe Ratio**: Risk-adjusted returns accounting for volatility

## Architecture

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

## Technical Stack

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript
- **Visualization**: Plotly.js, Recharts, D3
- **Styling**: Tailwind CSS
- **Build Tool**: Vite

### Backend (Python + FastAPI)
- **API**: FastAPI with Uvicorn
- **Data**: Pandas, NumPy, Datasets (Hugging Face)
- **Caching**: Cachetools
- **Cloud**: Google Cloud Storage, Secret Manager

### Core Engine (Python)
- **Agent Framework**: [smolagents](https://github.com/huggingface/smolagents) for multi-tool AI agents
- **LLM Integration**: LiteLLM, OpenAI API
- **Web Scraping**: Playwright, Scrapfly SDK
- **Market Data**: py-clob-client for Polymarket integration
- **Scheduling**: APScheduler for automated predictions

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js 18+
- Docker (optional, for containerized deployment)

### Environment Variables
See [ENV_VARIABLES.md](ENV_VARIABLES.md) for a complete guide on configuring all required environment variables.

### Local Development

#### Frontend
```bash
cd predibench-frontend-react
npm install
npm run dev
```

#### Backend
```bash
cd predibench-backend
uv sync
uv run uvicorn main:app --reload
```

#### Core Engine
```bash
cd predibench-core
uv sync
# Run predictions
uv run python scripts/run_predictions.py
```

### Docker Deployment
```bash
docker build -t predibench .
docker run -p 8000:8000 predibench
```

## Methods

### Agent Framework
All models run under a shared [smolagents](https://github.com/huggingface/smolagents) setup with:
- **CodeAgent** (multi-tool calls) as default
- **ToolCallingAgent** for compatible models (OpenAI, DeepSeek)
- Native frameworks for specialized models (DeepResearch)

### Event Selection Strategy
1. Top 10 trending Polymarket events by weekly volume
2. Events must resolve within 2 months
3. Crypto events excluded for stability
4. Regular rotation to capture market dynamics

### Prediction Process
1. Models analyze event context
2. Web search for relevant information
3. Probability estimation and bet decision
4. Performance tracking across time horizons

## Key Findings

### Model Performance
- Stronger models produce probability estimates closer to market odds
- Information retrieval depth correlates with success (16+ sources optimal)
- Bet-edge consistency (>5% threshold) correlates with profitability
- Market predictions become markedly more accurate 3 days before resolution

### Market Dynamics
- News events can cause 40%+ price swings within hours
- Brier scores decrease significantly as events approach resolution
- Positions should typically be held for <7 days for optimal returns

## Citation

```bibtex
@Misc{predibench,
  title =        {PrediBench: a live benchmark to measure LLM's ability to predict the future},
  author =       {Charles Azam and Aymeric Roucher},
  howpublished = {\url{https://github.com/PresageLabs/PrediBench}},
  year =         {2025}
}
```

## License

This project is open source. Please check individual component licenses for details.

## Contributing

We welcome contributions! Please see our contributing guidelines for more information.

## Links

- **Live Leaderboard**: [predibench.com](https://predibench.com)
- **GitHub**: [github.com/PresageLabs/PrediBench](https://github.com/PresageLabs/PrediBench)
- **Dataset**: [Huggingface Dataset](https://huggingface.co/datasets/PresageLabs/PrediBench)
