"""
config/settings.py - Central configuration for the trading bot
"""
import os
from enum import Enum
from dataclasses import dataclass
# ============================================================================
# TRADING PARAMETERS
# ============================================================================
@dataclass
class TradingConfig:
    """Trading strategy configuration."""
    
    # Capital Management
    TOTAL_CAPITAL = 50000              # Total account capital
    CAPITAL_PER_TRADE = 2500           # Risk per trade (5% of capital)
    MAX_CONCURRENT_TRADES = 5          # Max open positions
    DAILY_LOSS_LIMIT_PCT = 0.12        # Stop trading if down 12%
    
    # Entry Criteria
    MIN_ENTRY_CONFIDENCE = 70          # Only trade if 70%+ confidence
    REQUIRE_MULTI_TF_ALIGNMENT = True  # Need 4h + 1d + 1w aligned
    MIN_LIQUIDITY_VOLUME = 50          # Min option volume
    MIN_LIQUIDITY_OI = 200             # Min open interest
    
    # Volatility Rules
    MAX_IV_PERCENTILE = 75             # Don't buy if IV too high
    MIN_IV_PERCENTILE = 25             # Wait if IV too low
    MAX_EARNINGS_DAYS_BEFORE = 14      # Skip if earnings soon
    MAX_EARNINGS_DAYS_AFTER = 3        # Skip if just had earnings
    
    # DTE Selection
    MIN_DTE = 14                       # Minimum days to expiration
    MAX_DTE = 60                       # Maximum days to expiration
    OPTIMAL_DTE_RANGE = (21, 45)       # Ideal DTE range
    
    # Greeks Targets
    DELTA_RANGE_HIGH_IV = (0.25, 0.45)     # More OTM when IV high
    DELTA_RANGE_NORMAL_IV = (0.35, 0.55)   # Standard ATM
    DELTA_RANGE_LOW_IV = (0.40, 0.65)      # More ITM when IV low
    MAX_THETA_RISK = 0.02              # Max daily theta decay
    MAX_VEGA_EXPOSURE = 0.05           # Max vega exposure
    
    # Exit Strategy
    PROFIT_TARGET_MULTIPLIERS = [1.25, 1.50, 2.00]  # 25%, 50%, 100% gains
    PROFIT_TIER_ALLOCATIONS = [0.50, 0.30, 0.20]    # Sell 50%, 30%, 20%
    STOP_LOSS_PCT = -30                # Fixed stop at -30%
    TRAILING_STOP_PCT = -25            # Trailing stop from peak
    MIN_DTE_AUTO_EXIT = 5              # Auto exit if < 5 DTE
    
    # Risk Management
    MIN_RISK_REWARD_RATIO = 2.0        # Only trade 2:1 or better
    MIN_PROBABILITY_OF_PROFIT = 0.55   # At least 55% win rate needed
    MAX_CONSECUTIVE_LOSSES = 3         # Stop after 3 losses
    POSITION_SIZE_REDUCTION = 0.5      # Reduce by 50% after loss
    
    # Timing
    SCAN_INTERVAL_SECONDS = 300        # Run scans every 5 minutes
    MONITOR_INTERVAL_SECONDS = 60      # Check positions every 60 seconds
    MARKET_OPEN_HOUR = 9               # Market opens at 9:30 AM ET
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 16             # Market closes at 4:00 PM ET
    MARKET_CLOSE_MINUTE = 0
    
    # Data Sources
    TICKERS_FILE = "config/tickers.csv"
    SCAN_YAHOO_SCREENER = True         # Include most-active stocks
    MAX_TICKERS_PER_SCAN = 20          # Analyze max 20 tickers
@dataclass
class APIConfig:
    """API credentials and endpoints."""
    
    # Alpaca (Paper Trading)
    ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID", "")
    ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY", "")
    ALPACA_BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    
    # Yahoo Finance (Free)
    YAHOO_TIMEOUT = 10                 # API timeout
    
    # Ollama (Local LLM - for research only)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_TIMEOUT = 30
@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    DB_PATH = "data/trades.db"
    BACKUP_PATH = "data/backups/"
    AUTO_BACKUP = True
    BACKUP_INTERVAL_HOURS = 24
@dataclass
class DashboardConfig:
    """Web dashboard configuration."""
    
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = False
    REFRESH_INTERVAL_SECONDS = 10
    MAX_RECENT_TRADES = 50
# ============================================================================
# TECHNICAL ANALYSIS THRESHOLDS
# ============================================================================
class TechnicalThresholds(Enum):
    """Technical analysis signal thresholds."""
    
    # RSI (Relative Strength Index)
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    RSI_VERY_OVERBOUGHT = 80
    RSI_VERY_OVERSOLD = 20
    
    # MACD
    MACD_DIVERGENCE_THRESHOLD = 0.001
    
    # Stochastic RSI
    STOCH_RSI_THRESHOLD = 0.20
    
    # Bollinger Bands
    BB_STDDEV = 2.0
    
    # Volume
    MIN_DAILY_VOLUME_MULTIPLIER = 0.5  # 50% of average
# ============================================================================
# LOGGING
# ============================================================================
class LogConfig:
    """Logging configuration."""
    
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = "logs/trading_bot.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
    LOG_BACKUP_COUNT = 5
# ============================================================================
# MARKET HOURS (Eastern Time)
# ============================================================================
MARKET_HOURS = {
    "regular_open": (9, 30),
    "regular_close": (16, 0),
    "pre_market_open": (4, 0),
    "after_hours_close": (20, 0),
}
# ============================================================================
# ERROR THRESHOLDS
# ============================================================================
class ErrorConfig:
    """Error handling configuration."""
    
    MAX_API_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    API_TIMEOUT_SECONDS = 30
    CONNECTION_ERROR_THRESHOLD = 5    # Stop if 5 consecutive failures