"""
api/yahoo_client.py - Yahoo Finance API wrapper
Already implemented in data_fetcher.py, but consolidated here for consistency
"""

from core.data_fetcher import DataFetcher
from config.logger import logger

class YahooClient:
    """Yahoo Finance API wrapper."""
    
    def __init__(self):
        self.logger = logger
        self.fetcher = DataFetcher()
    
    def get_stock_data(self, ticker: str) -> dict:
        """Get stock data from Yahoo Finance."""
        return self.fetcher.get_stock_data(ticker)
    
    def get_options_chain(self, ticker: str, min_dte: int = 14, max_dte: int = 60) -> dict:
        """Get options chain."""
        return self.fetcher.get_options_chain(ticker, min_dte, max_dte)
    
    def get_earnings(self, ticker: str) -> dict:
        """Get earnings data."""
        return self.fetcher.get_earnings_data(ticker)
    
    def get_news(self, ticker: str, limit: int = 5) -> list:
        """Get news headlines."""
        return self.fetcher.get_news(ticker, limit)
    
    def get_vix(self) -> dict:
        """Get VIX level."""
        return self.fetcher.get_vix()
