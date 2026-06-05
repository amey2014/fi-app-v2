"""
api/alpaca_client.py - Alpaca API client wrapper
Handles all communication with Alpaca Trading API v2
"""
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
logger = logging.getLogger(__name__)
class AlpacaClient:
    """
    Alpaca API Client v2 - Uses REST API
    """
    
    def __init__(self):
        """Initialize Alpaca API client."""
        
        logger.info("Initializing Alpaca client...")
        
        # Get credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.secret_key = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        self.data_url = 'https://data.alpaca.markets'
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Missing APCA_API_KEY_ID or APCA_API_SECRET_KEY in .env")
        
        # Set up headers
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
        }
        
        logger.info(f"    Base URL: {self.base_url}")
        logger.info(f"    Data URL: {self.data_url}")
        
        # Test connection
        try:
            account = self.get_account()
            if 'error' not in account:
                logger.info("[OK] Alpaca client initialized successfully")
                logger.info(f"    Account Status: {account.get('status')}")
            else:
                logger.warning(f"Could not verify account: {account.get('error')}")
        except Exception as e:
            logger.warning(f"Could not verify connection: {e}")
    
    # =========================================================================
    # ACCOUNT METHODS
    # =========================================================================
    
    def get_account(self) -> dict:
        """
        Get account details.
        
        Returns account information including:
        - Cash balance
        - Portfolio value (equity)
        - Buying power
        - Margin information
        - Account status and flags
        
        Reference: GET /v2/account
        """
        try:
            resp = requests.get(
                f'{self.base_url}/v2/account',
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                # IDs
                'id': data.get('id'),
                'account_number': data.get('account_number'),
                
                # Core values
                'cash': float(data.get('cash', 0)),
                'equity': float(data.get('equity', 0)),  # Cash + long - short
                'portfolio_value': float(data.get('portfolio_value', 0)),  # Same as equity (deprecated)
                'long_market_value': float(data.get('long_market_value', 0)),
                'short_market_value': float(data.get('short_market_value', 0)),
                
                # Buying power
                'buying_power': float(data.get('buying_power', 0)),
                'daytrading_buying_power': float(data.get('daytrading_buying_power', 0)),  # DEPRECATED
                'regt_buying_power': float(data.get('regt_buying_power', 0)),  # Reg T buying power
                'non_marginable_buying_power': float(data.get('non_marginable_buying_power', 0)),
                'options_buying_power': float(data.get('options_buying_power', 0)),
                
                # Margin info
                'multiplier': int(data.get('multiplier', 1)),  # 1, 2, or 4
                'initial_margin': float(data.get('initial_margin', 0)),
                'maintenance_margin': float(data.get('maintenance_margin', 0)),
                'last_equity': float(data.get('last_equity', 0)),
                'last_maintenance_margin': float(data.get('last_maintenance_margin', 0)),
                'sma': float(data.get('sma', 0)),  # Special memorandum account
                
                # Status flags
                'status': data.get('status'),  # ACTIVE, ONBOARDING, etc.
                'account_blocked': bool(data.get('account_blocked', False)),
                'trading_blocked': bool(data.get('trading_blocked', False)),
                'transfers_blocked': bool(data.get('transfers_blocked', False)),
                'trade_suspended_by_user': bool(data.get('trade_suspended_by_user', False)),
                
                # Trading permissions
                'shorting_enabled': bool(data.get('shorting_enabled', False)),
                'pattern_day_trader': bool(data.get('pattern_day_trader', False)),  # DEPRECATED
                'daytrade_count': int(data.get('daytrade_count', 0)),  # DEPRECATED
                
                # Options
                'options_approved_level': int(data.get('options_approved_level', 0)),  # 0-3
                'options_trading_level': int(data.get('options_trading_level', 0)),  # 0-3
                
                # Transfers
                'pending_transfer_in': float(data.get('pending_transfer_in', 0)),
                'pending_transfer_out': float(data.get('pending_transfer_out', 0)),
                
                # Fees
                'accrued_fees': float(data.get('accrued_fees', 0)),
                'pending_reg_taf_fees': float(data.get('pending_reg_taf_fees', 0)),
                
                # Metadata
                'created_at': data.get('created_at'),
                'currency': data.get('currency', 'USD'),
                'balance_asof': data.get('balance_asof'),
                'intraday_adjustments': float(data.get('intraday_adjustments', 0)),
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {'error': str(e)}
    
    def is_market_open(self) -> bool:
        """Check if market is open."""
        try:
            resp = requests.get(
                f'{self.base_url}/v2/clock',
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('is_open', False)
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    # =========================================================================
    # MARKET DATA METHODS
    # =========================================================================
    
    def get_bars(self, symbol: str, timeframe: str = '5Min', limit: int = 100):
        """
        Get historical bars (OHLCV data).
        
        Endpoint: GET /v2/stocks/bars
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: '1Min', '5Min', '15Min', '1Hour', '1Day', etc.
            limit: Number of bars (1-10000)
        
        Returns:
            List of BarData objects or None
        """
        try:
            # Calculate start date
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            logger.debug(
                f"Fetching {symbol}: timeframe={timeframe}, "
                f"start={start_date}, limit={limit}"
            )
            
            resp = requests.get(
                f'{self.data_url}/v2/stocks/bars',
                params={
                    'symbols': symbol,
                    'timeframe': timeframe,
                    'start': start_date,
                    'limit': limit,
                    'adjustment': 'all',
                    'sort': 'asc',
                },
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 404:
                logger.warning(f"Symbol {symbol} not found (404)")
                return None
            
            if resp.status_code == 400:
                error_msg = resp.json().get('message', 'Unknown error')
                logger.warning(f"Bad request for {symbol}: {error_msg}")
                return None
            
            resp.raise_for_status()
            data = resp.json()
            
            if 'bars' in data and symbol in data['bars']:
                bars = data['bars'][symbol]
                logger.debug(f"Got {len(bars)} bars for {symbol}")
                return [BarData(b) for b in bars]
            else:
                logger.warning(f"No bars found for {symbol}")
                return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching bars for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {e}")
            return None
    
    def get_latest_bar(self, symbol: str):
        """Get latest bar for a symbol."""
        try:
            resp = requests.get(
                f'{self.data_url}/v2/stocks/bars',
                params={
                    'symbols': symbol,
                    'timeframe': '1Min',
                    'limit': 1,
                },
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 404:
                logger.debug(f"Symbol {symbol} not found (404)")
                return None
            
            resp.raise_for_status()
            data = resp.json()
            
            if 'bars' in data and symbol in data['bars']:
                bars = data['bars'][symbol]
                if bars:
                    return BarData(bars[-1])
            
            return None
        
        except Exception as e:
            logger.debug(f"Error getting latest bar for {symbol}: {e}")
            return None
    
    def get_latest_quote(self, symbol: str):
        """Get latest quote for a symbol (bid/ask)."""
        try:
            resp = requests.get(
                f'{self.data_url}/v2/stocks/quotes',
                params={
                    'symbols': symbol,
                },
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 404:
                return None
            
            resp.raise_for_status()
            data = resp.json()
            
            if 'quotes' in data and symbol in data['quotes']:
                return QuoteData(data['quotes'][symbol])
            
            return None
        
        except Exception as e:
            logger.debug(f"Error getting latest quote for {symbol}: {e}")
            return None
    
    # =========================================================================
    # ORDER METHODS
    # =========================================================================
    
    def submit_order(self, symbol: str, qty: int, side: str,
                    order_type: str = 'market', limit_price: float = None) -> dict:
        """
        Submit an order.
        
        Endpoint: POST /v2/orders
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            limit_price: Limit price (required for limit orders)
        
        Returns:
            Order details dictionary
        """
        try:
            payload = {
                'symbol': symbol,
                'qty': qty,
                'side': side.lower(),
                'type': order_type.lower(),
                'time_in_force': 'day',
            }
            
            if order_type.lower() == 'limit' and limit_price:
                payload['limit_price'] = limit_price
            
            resp = requests.post(
                f'{self.base_url}/v2/orders',
                json=payload,
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            logger.info(f"Order submitted: {symbol} {side} {qty}")
            
            return {
                'order_id': data.get('id'),
                'symbol': data.get('symbol'),
                'qty': data.get('qty'),
                'side': data.get('side'),
                'status': data.get('status'),
                'filled_qty': data.get('filled_qty', 0),
            }
        
        except Exception as e:
            logger.error(f"Error submitting order for {symbol}: {e}")
            return {'error': str(e)}
    
    def get_orders(self, status: str = 'all') -> list:
        """
        Get all orders.
        
        Endpoint: GET /v2/orders
        
        Args:
            status: 'all', 'open', 'closed', 'pending_new', 'accepted', etc.
        
        Returns:
            List of order objects
        """
        try:
            resp = requests.get(
                f'{self.base_url}/v2/orders',
                params={'status': status, 'limit': 100},
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Endpoint: DELETE /v2/orders/{order_id}
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if cancelled successfully
        """
        try:
            resp = requests.delete(
                f'{self.base_url}/v2/orders/{order_id}',
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    # =========================================================================
    # POSITION METHODS
    # =========================================================================
    
    def get_positions(self) -> list:
        """
        Get all open positions.
        
        Endpoint: GET /v2/positions
        
        Returns:
            List of position objects
        """
        try:
            resp = requests.get(
                f'{self.base_url}/v2/positions',
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str):
        """
        Get specific position.
        
        Endpoint: GET /v2/positions/{symbol}
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position object or None
        """
        try:
            resp = requests.get(
                f'{self.base_url}/v2/positions/{symbol}',
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.debug(f"No position for {symbol}: {e}")
            return None
    
    def close_position(self, symbol: str, qty: int = None) -> bool:
        """
        Close a position.
        
        Endpoint: DELETE /v2/positions/{symbol}
        
        Args:
            symbol: Stock symbol
            qty: Quantity (None = close entire position)
        
        Returns:
            True if closed successfully
        """
        try:
            if qty is None:
                resp = requests.delete(
                    f'{self.base_url}/v2/positions/{symbol}',
                    headers=self.headers,
                    timeout=10
                )
                resp.raise_for_status()
            else:
                self.submit_order(symbol, qty, 'sell')
            
            logger.info(f"Position closed for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
# ============================================================================
# HELPER CLASSES
# ============================================================================
class BarData:
    """OHLCV bar data container."""
    def __init__(self, data: dict):
        self.t = data.get('t')  # timestamp
        self.o = float(data.get('o', 0))  # open
        self.h = float(data.get('h', 0))  # high
        self.l = float(data.get('l', 0))  # low
        self.c = float(data.get('c', 0))  # close
        self.v = int(data.get('v', 0))    # volume
        self.n = int(data.get('n', 0))    # number of trades
        self.vw = float(data.get('vw', 0))  # volume weighted avg price
    
    def __repr__(self):
        return f"Bar(c={self.c:.2f}, v={self.v})"
class QuoteData:
    """Quote data container (bid/ask)."""
    def __init__(self, data: dict):
        self.t = data.get('t')  # timestamp
        self.ax = data.get('ax')  # ask exchange
        self.ap = float(data.get('ap', 0))  # ask price
        self.as_ = int(data.get('as', 0))   # ask size
        self.bx = data.get('bx')  # bid exchange
        self.bp = float(data.get('bp', 0))  # bid price
        self.bs = int(data.get('bs', 0))    # bid size
    
    def mid_price(self) -> float:
        """Get mid price (average of bid and ask)."""
        if self.bp > 0 and self.ap > 0:
            return (self.bp + self.ap) / 2
        elif self.ap > 0:
            return self.ap
        else:
            return self.bp