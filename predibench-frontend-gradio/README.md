---
title: PrediBench Frontend
emoji: 🏆
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.42.0
app_file: app.py
pinned: false
license: apache-2.0
---

# PrediBench Frontend

Interactive leaderboard and performance dashboard for AI agent predictions on Polymarket.

## Features

- 🏆 **Leaderboard Tab**: Rankings by Profit, Sharpe ratio, win rate
- 📈 **Performance Tab**: Interactive charts with agent selection
- 🔄 **Daily Refresh**: Loads latest data from HuggingFace datasets
- 📱 **Responsive UI**: Clean Gradio interface

## Data Source

Loads from:
- `m-ric/predibench-agent-choices`

## Usage

1. View overall leaderboard in the first tab
2. Select specific agents in the performance tab
3. Explore interactive Plotly visualizations
4. Refresh data anytime with the button