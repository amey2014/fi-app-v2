"""
core/data_fetcher.py - Market data collection from multiple sources
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from config.logger import logger
from config.settings import TradingConfig, APIConfig
from utils.helpers import is_market_open
import requests
import time
class DataFetcher:
    """Fetch market data from Yahoo Finance."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
        self.api_config = APIConfig()
        self.cache = {}
        self.cache_timestamp = {}
        self.cache_duration = 300  # 5 minutes
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self.cache_timestamp:
            return False
        
        age = (datetime.now() - self.cache_timestamp[key]).total_seconds()
        return age < self.cache_duration
    
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get data from cache if valid."""
        if self._is_cache_valid(key):
            return self.cache[key]
        return None
    
    def _set_cache(self, key: str, data: Dict):
        """Store data in cache."""
        self.cache[key] = data
        self.cache_timestamp[key] = datetime.now()
    
    # =========================================================================
    # STOCK DATA FETCHING
    # =========================================================================
    
    def get_stock_data(self, ticker: str) -> Dict:
        """
        Fetch comprehensive stock data.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dict with stock information
        """
        
        cache_key = f"stock_{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data for analysis
            hist = stock.history(period="1y")
            
            if hist.empty:
                logger.warning(f"No historical data for {ticker}")
                return {"error": f"No data for {ticker}"}
            
            # Current price and fundamentals
            info = stock.info or {}
            current_price = info.get("currentPrice") or hist["Close"].iloc[-1]
            
            data = {
                "ticker": ticker,
                "price": float(current_price),
                "timestamp": datetime.now().isoformat(),
                
                # Price levels
                "high_52w": float(info.get("fiftyTwoWeekHigh", 0)),
                "low_52w": float(info.get("fiftyTwoWeekLow", 0)),
                "previous_close": float(hist["Close"].iloc[-2] if len(hist) > 1 else current_price),
                
                # Volume
                "volume": int(info.get("volume", 0)),
                "avg_volume_3m": int(info.get("averageVolume", 0)),
                "volume_change_pct": float(
                    ((hist["Volume"].iloc[-1] - hist["Volume"].mean()) / hist["Volume"].mean() * 100)
                    if hist["Volume"].mean() > 0 else 0
                ),
                
                # Performance metrics
                "change_pct_1d": float(
                    ((current_price - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100)
                    if len(hist) > 1 else 0
                ),
                "change_pct_1w": float(
                    ((current_price - hist["Close"].iloc[-5]) / hist["Close"].iloc[-5] * 100)
                    if len(hist) > 5 else 0
                ),
                "change_pct_1m": float(
                    ((current_price - hist["Close"].iloc[-20]) / hist["Close"].iloc[-20] * 100)
                    if len(hist) > 20 else 0
                ),
                "change_pct_3m": float(
                    ((current_price - hist["Close"].iloc[-60]) / hist["Close"].iloc[-60] * 100)
                    if len(hist) > 60 else 0
                ),
                "change_pct_ytd": float(
                    ((current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100)
                    if len(hist) > 0 else 0
                ),
                
                # Fundamentals
                "pe_ratio": float(info.get("trailingPE", 0)) or None,
                "eps": float(info.get("trailingEps", 0)) or None,
                "market_cap": int(info.get("marketCap", 0)) or None,
                "beta": float(info.get("beta", 0)) or 1.0,
                
                # Moving averages
                "ma_50": float(hist["Close"].tail(50).mean()) if len(hist) >= 50 else None,
                "ma_200": float(hist["Close"].tail(200).mean()) if len(hist) >= 200 else None,
                
                # Volatility (Historical)
                "volatility_30d": float(hist["Close"].pct_change().tail(30).std() * np.sqrt(252) * 100),
                "volatility_90d": float(hist["Close"].pct_change().tail(90).std() * np.sqrt(252) * 100),
                
                # Trend direction
                "price_above_ma50": current_price > hist["Close"].tail(50).mean() if len(hist) >= 50 else None,
                "price_above_ma200": current_price > hist["Close"].tail(200).mean() if len(hist) >= 200 else None,
                "ma50_above_ma200": (
                    hist["Close"].tail(50).mean() > hist["Close"].tail(200).mean()
                    if len(hist) >= 200 else None
                ),
            }
            
            self._set_cache(cache_key, data)
            return data
        
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # OPTIONS CHAIN FETCHING
    # =========================================================================
    
    def get_options_chain(self, ticker: str, min_dte: int = 14, max_dte: int = 60) -> Dict:
        """
        Fetch options chain with filtered contracts.
        
        Args:
            ticker: Stock ticker
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
        
        Returns:
            Dict with calls and puts
        """
        
        cache_key = f"options_{ticker}_{min_dte}_{max_dte}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                logger.warning(f"No options available for {ticker}")
                return {"calls": [], "puts": []}
            
            all_calls = []
            all_puts = []
            
            today = datetime.now().date()
            
            for exp_date in expirations:
                exp = datetime.strptime(exp_date, "%Y-%m-%d").date()
                dte = (exp - today).days
                
                # Filter by DTE
                if dte < min_dte or dte > max_dte:
                    continue
                
                try:
                    chain = stock.option_chain(exp_date)
                    
                    # Process calls
                    calls = chain.calls
                    calls = calls[calls["volume"] > 0]  # Must have volume
                    calls["dte"] = dte
                    calls["expiry"] = exp_date
                    all_calls.append(calls)
                    
                    # Process puts
                    puts = chain.puts
                    puts = puts[puts["volume"] > 0]  # Must have volume
                    puts["dte"] = dte
                    puts["expiry"] = exp_date
                    all_puts.append(puts)
                
                except Exception as e:
                    logger.warning(f"Error fetching options for {ticker} exp {exp_date}: {e}")
                    continue
            
            # Combine and filter
            calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
            puts_df = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()
            
            # Filter by liquidity
            calls_filtered = self._filter_by_liquidity(calls_df)
            puts_filtered = self._filter_by_liquidity(puts_df)
            
            result = {
                "calls": calls_filtered,
                "puts": puts_filtered,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
            }
            
            self._set_cache(cache_key, result)
            return result
        
        except Exception as e:
            logger.error(f"Error fetching options chain for {ticker}: {e}")
            return {"calls": [], "puts": [], "error": str(e)}
    
    def _filter_by_liquidity(self, df: pd.DataFrame) -> List[Dict]:
        """Filter options by liquidity criteria."""
        
        if df.empty:
            return []
        
        # Apply filters
        filtered = df[
            (df["volume"] >= self.config.MIN_LIQUIDITY_VOLUME) &
            (df["openInterest"] >= self.config.MIN_LIQUIDITY_OI)
        ]
        
        # Convert to list of dicts
        return filtered.to_dict("records")
    
    # =========================================================================
    # EARNINGS DATA
    # =========================================================================
    
    def get_earnings_data(self, ticker: str) -> Dict:
        """
        Get next earnings date for a ticker.
        
        Args:
            ticker: Stock ticker
        
        Returns:
            Dict with earnings information
        """
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            
            earnings_date = info.get("earningsDate")
            
            if earnings_date:
                # earnings_date can be a list or single value
                if isinstance(earnings_date, list) and len(earnings_date) > 0:
                    earnings_date = earnings_date[0]
                
                if hasattr(earnings_date, 'date'):
                    earnings_date = earnings_date.date()
                
                today = datetime.now().date()
                days_until = (earnings_date - today).days
                
                return {
                    "has_earnings": True,
                    "earnings_date": str(earnings_date),
                    "days_until_earnings": days_until,
                    "earnings_soon": (0 <= days_until <= self.config.MAX_EARNINGS_DAYS_BEFORE),
                    "just_had_earnings": (
                        -self.config.MAX_EARNINGS_DAYS_AFTER <= days_until < 0
                    ),
                }
            else:
                return {
                    "has_earnings": False,
                    "earnings_date": None,
                    "days_until_earnings": None,
                    "earnings_soon": False,
                    "just_had_earnings": False,
                }
        
        except Exception as e:
            logger.warning(f"Error fetching earnings for {ticker}: {e}")
            return {
                "has_earnings": False,
                "error": str(e),
            }
    
    # =========================================================================
    # NEWS DATA
    # =========================================================================
    
    def get_news(self, ticker: str, limit: int = 5) -> List[Dict]:
        """
        Fetch recent news headlines for a ticker.
        
        Args:
            ticker: Stock ticker
            limit: Number of headlines to fetch
        
        Returns:
            List of news articles
        """
        
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                return []
            
            articles = []
            for item in news[:limit]:
                articles.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "source": item.get("source", ""),
                    "published": item.get("providerPublishTime", 0),
                })
            
            return articles
        
        except Exception as e:
            logger.warning(f"Error fetching news for {ticker}: {e}")
            return []
    
    # =========================================================================
    # VIX DATA
    # =========================================================================
    
    def get_vix(self) -> Dict:
        """
        Fetch current VIX level.
        
        Returns:
            Dict with VIX data
        """
        
        cache_key = "vix"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1y")
            
            if hist.empty:
                return {"error": "No VIX data available"}
            
            current_vix = hist["Close"].iloc[-1]
            vix_20d_avg = hist["Close"].tail(20).mean()
            vix_52w_high = hist["Close"].max()
            vix_52w_low = hist["Close"].min()
            
            result = {
                "vix": float(current_vix),
                "vix_20d_avg": float(vix_20d_avg),
                "vix_52w_high": float(vix_52w_high),
                "vix_52w_low": float(vix_52w_low),
                "vix_percentile": float(
                    (current_vix - vix_52w_low) / (vix_52w_high - vix_52w_low) * 100
                    if vix_52w_high > vix_52w_low else 50
                ),
                "timestamp": datetime.now().isoformat(),
            }
            
            self._set_cache(cache_key, result)
            return result
        
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # SCREENER DATA
    # =========================================================================
    
    def get_most_active_stocks(self, limit: int = 20) -> List[str]:
        """
        Get most active stocks from Yahoo Finance screener.
        
        Args:
            limit: Number of stocks to fetch
        
        Returns:
            List of ticker symbols
        """
        
        cache_key = "most_active"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # Yahoo Finance most active screener
            url = "https://finance.yahoo.com/most-active"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=self.api_config.YAHOO_TIMEOUT)
            response.raise_for_status()
            
            # Parse HTML to extract tickers
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")
            
            tickers = []
            # Find all ticker links in the screener
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/quote/" in href:
                    ticker = href.split("/quote/")[-1].split("?")[0]
                    if ticker and len(ticker) <= 5:  # Valid ticker length
                        tickers.append(ticker.upper())
                
                if len(tickers) >= limit:
                    break
            
            self._set_cache(cache_key, tickers)
            return tickers
        
        except Exception as e:
            logger.warning(f"Error fetching most active stocks: {e}")
            return []
    
    # =========================================================================
    # TICKER LIST MANAGEMENT
    # =========================================================================
    
    def load_ticker_list(self, filepath: str = None) -> List[str]:
        """
        Load ticker list from CSV file.
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            List of ticker symbols
        """
        
        if filepath is None:
            filepath = self.config.TICKERS_FILE
        
        try:
            df = pd.read_csv(filepath)
            
            # Expect a column named 'ticker' or 'Ticker'
            ticker_col = None
            for col in df.columns:
                if col.lower() == "ticker":
                    ticker_col = col
                    break
            
            if ticker_col is None:
                logger.error(f"No 'ticker' column found in {filepath}")
                return []
            
            tickers = df[ticker_col].dropna().unique().tolist()
            tickers = [t.upper().strip() for t in tickers]
            
            logger.info(f"Loaded {len(tickers)} tickers from {filepath}")
            return tickers
        
        except Exception as e:
            logger.error(f"Error loading ticker list from {filepath}: {e}")
            return []
    
    def get_scan_tickers(self) -> List[str]:
        """
        Get combined list of tickers for scanning.
        Includes both CSV file and screener results.
        
        Returns:
            List of unique ticker symbols
        """
        
        tickers = set()
        
        # Load from CSV
        csv_tickers = self.load_ticker_list()
        tickers.update(csv_tickers)
        
        # Add from screener
        if self.config.SCAN_YAHOO_SCREENER:
            screener_tickers = self.get_most_active_stocks(
                limit=self.config.MAX_TICKERS_PER_SCAN
            )
            tickers.update(screener_tickers)
        
        # Remove invalid tickers
        valid_tickers = [t for t in tickers if len(t) <= 5]
        
        logger.info(f"Scan will analyze {len(valid_tickers)} tickers")
        return list(valid_tickers)[:self.config.MAX_TICKERS_PER_SCAN]