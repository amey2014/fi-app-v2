# 🤖 Professional Options Trading Bot

A production-grade options trading system built with Python, designed for algorithmic trading of equity options with sophisticated risk management and real-time monitoring.

## 🎯 Features

### Core Trading System
- **Intelligent Entry Analysis**: Multi-timeframe technical analysis (4H, 1D, 1W)
- **Volatility-Aware Trading**: IV percentile analysis, Greeks calculations
- **Smart Contract Selection**: Optimal strike/DTE selection based on multiple criteria
- **Risk Management**: Dynamic position sizing, trailing stops, profit targets
- **Deterministic Decision Engine**: No guessing—every trade decision is rule-based

### Position Management
- **Real-Time Monitoring**: Track positions with live Greeks updates
- **Intelligent Exit Management**: Multiple exit conditions (stops, profit targets, DTE)
- **Partial Position Closure**: Scale out of winning trades
- **Recovery Logic**: Configurable re-entry after losses

### Market Data & Analysis
- **Multi-Source Data**: Yahoo Finance + Alpaca for reliable data
- **Technical Indicators**: RSI, MACD, Stochastic RSI, Bollinger Bands, ATR, OBV
- **IV/Greeks Analysis**: Black-Scholes Greeks calculation
- **Earnings Detection**: Automatic skip on earnings dates
- **Market Context**: VIX monitoring, market hours checking

### Persistence & Analytics
- **SQLite Database**: Complete trade history and analytics
- **Trade Logging**: Detailed entry/exit logging with metadata
- **Performance Reports**: Win rate, profit factor, drawdown analysis
- **Backtesting Support**: Historical trade simulation (future)

### Web Dashboard
- **Real-Time Monitoring**: Live account and position tracking
- **Manual Controls**: Pause/resume trading, manual exits
- **Performance Metrics**: Win rate, P&L, Greeks exposure
- **Alert System**: Real-time notifications and warnings

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Alpaca trading account (https://alpaca.markets)
- Virtual environment (recommended)

### Installation

1. **Clone/Download the project**
```bash
cd options_trading_bot
