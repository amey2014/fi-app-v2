"""
utils/helpers.py - Utility functions
"""
from datetime import datetime, timedelta
import pytz
from typing import Tuple
from config.logger import logger
def is_market_open(check_time: datetime = None) -> bool:
    """
    Check if US stock market is open.
    
    Args:
        check_time: Time to check (defaults to now in ET)
    
    Returns:
        True if market is open, False otherwise
    """
    
    if check_time is None:
        et = pytz.timezone("America/New_York")
        check_time = datetime.now(et)
    
    # Market hours: 9:30 AM - 4:00 PM ET, Mon-Fri
    if check_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    market_open = check_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = check_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= check_time <= market_close
def get_business_days_remaining(from_date: datetime, to_date: datetime) -> int:
    """
    Calculate business days between two dates.
    
    Args:
        from_date: Start date
        to_date: End date
    
    Returns:
        Number of business days
    """
    business_days = 0
    current = from_date
    
    while current <= to_date:
        if current.weekday() < 5:  # Mon-Fri
            business_days += 1
        current += timedelta(days=1)
    
    return business_days
def parse_option_symbol(symbol: str) -> dict:
    """
    Parse Alpaca option symbol format.
    
    Format: {TICKER}{YYMMDD}{C/P}{8-digit strike padded}
    Example: AAPL240119C00450000
    
    Args:
        symbol: Option symbol string
    
    Returns:
        Dict with parsed components
    
    Raises:
        ValueError: If symbol format invalid
    """
    
    try:
        # Extract ticker (letters at start)
        i = 0
        while i < len(symbol) and symbol[i].isalpha():
            i += 1
        
        if i == 0 or i >= len(symbol):
            raise ValueError("Invalid symbol format")
        
        ticker = symbol[:i]
        rest = symbol[i:]
        
        # Extract date (YYMMDD)
        if len(rest) < 6:
            raise ValueError("Invalid date format")
        
        date_str = rest[:6]
        rest = rest[6:]
        
        # Extract type (C or P)
        if not rest or rest[0] not in ['C', 'P']:
            raise ValueError("Invalid option type")
        
        option_type = "CALL" if rest[0] == 'C' else "PUT"
        strike_str = rest[1:]
        
        # Parse components
        year = int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        
        # Handle century (assume 20xx)
        expiry = datetime(2000 + year, month, day).date()
        
        # Strike (8 digits, last 3 are decimals)
        strike = int(strike_str) / 1000.0
        
        # Calculate DTE
        dte = (expiry - datetime.now().date()).days
        
        return {
            "ticker": ticker,
            "expiry": expiry.isoformat(),
            "dte": dte,
            "strike": strike,
            "option_type": option_type,
            "original_symbol": symbol,
        }
    
    except Exception as e:
        logger.error(f"Failed to parse option symbol {symbol}: {e}")
        return {"error": str(e)}
def format_currency(amount: float) -> str:
    """Format number as currency."""
    return f"${amount:,.2f}"
def format_percentage(value: float, decimal_places: int = 2) -> str:
    """Format number as percentage."""
    return f"{value:+.{decimal_places}f}%"
def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")