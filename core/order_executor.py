"""
core/order_executor.py - Order placement and execution
Handles order validation, placement, and monitoring
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
from config.logger import logger
from config.settings import TradingConfig

class OrderExecutor:
    """Execute orders while maintaining risk controls."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
    
    # =========================================================================
    # ORDER VALIDATION
    # =========================================================================
    
    def validate_order(
        self,
        ticker: str,
        option_type: str,
        strike: float,
        contracts: int,
        entry_price: float,
        stock_price: float,
        available_capital: float,
        daily_loss: float = 0
    ) -> Dict:
        """
        Validate order before execution.
        
        Args:
            ticker: Stock ticker
            option_type: "CALL" or "PUT"
            strike: Strike price
            contracts: Number of contracts
            entry_price: Premium per contract
            stock_price: Current stock price
            available_capital: Available cash
            daily_loss: Current daily loss
        
        Returns:
            Dict with validation result
        """
        
        validation = {
            "valid": True,
            "checks": [],
            "warnings": [],
            "errors": [],
        }
        
        try:
            # CHECK 1: Strike sanity
            min_strike = stock_price * 0.5
            max_strike = stock_price * 1.5
            
            if not (min_strike <= strike <= max_strike):
                validation["errors"].append(
                    f"Strike ${strike} outside reasonable range (${min_strike:.2f}-${max_strike:.2f})"
                )
            else:
                validation["checks"].append(f"Strike ${strike} within range")
            
            # CHECK 2: Premium sanity
            max_premium = stock_price * 0.5  # Max 50% of stock price
            
            if entry_price > max_premium:
                validation["warnings"].append(
                    f"Premium ${entry_price} is high (>{max_premium:.2f})"
                )
            else:
                validation["checks"].append(f"Premium ${entry_price} reasonable")
            
            # CHECK 3: Capital available
            position_cost = contracts * entry_price * 100
            
            if position_cost > available_capital:
                validation["errors"].append(
                    f"Insufficient capital: need ${position_cost:.2f}, have ${available_capital:.2f}"
                )
            else:
                validation["checks"].append(f"Capital available (${position_cost:.2f})")
            
            # CHECK 4: Daily loss limit
            if daily_loss < (-self.config.TOTAL_CAPITAL * self.config.DAILY_LOSS_LIMIT_PCT):
                validation["errors"].append(
                    f"Daily loss limit exceeded (${daily_loss:.2f})"
                )
            else:
                validation["checks"].append("Within daily loss limit")
            
            # CHECK 5: Contracts reasonable
            if contracts < 1 or contracts > 100:
                validation["warnings"].append(
                    f"Unusual contract count: {contracts}"
                )
            else:
                validation["checks"].append(f"Contract count: {contracts}")
            
            # Final decision
            if validation["errors"]:
                validation["valid"] = False
            
            return validation
        
        except Exception as e:
            validation["errors"].append(f"Validation error: {e}")
            validation["valid"] = False
            return validation
    
    # =========================================================================
    # ORDER BUILDING
    # =========================================================================
    
    def build_order(
        self,
        ticker: str,
        option_type: str,
        strike: float,
        dte: int,
        contracts: int,
        side: str = "buy"
    ) -> Dict:
        """
        Build order details for Alpaca.
        
        Args:
            ticker: Stock ticker
            option_type: "CALL" or "PUT"
            strike: Strike price
            dte: Days to expiration
            contracts: Number of contracts
            side: "buy" or "sell"
        
        Returns:
            Dict with order details
        """
        
        try:
            # Build Alpaca symbol
            # Format: {TICKER}{YYMMDD}{C/P}{8-digit strike}
            
            expiry_date = self._calculate_expiry_date(dte)
            
            expiry_str = expiry_date.strftime("%y%m%d")
            option_type_char = "C" if option_type.upper() == "CALL" else "P"
            
            # Format strike as 8 digits with decimals (last 3 are decimals)
            strike_int = int(strike * 1000)
            strike_str = str(strike_int).zfill(8)
            
            symbol = f"{ticker}{expiry_str}{option_type_char}{strike_str}"
            
            qty = contracts  # Alpaca expects contracts, not shares
            
            return {
                "symbol": symbol,
                "ticker": ticker,
                "option_type": option_type,
                "strike": strike,
                "dte": dte,
                "expiry_date": expiry_str,
                "contracts": contracts,
                "shares": contracts * 100,
                "qty": qty,
                "side": side,
                "order_type": "market",  # Use market orders for reliability
                "time_in_force": "day",  # Day order
            }
        
        except Exception as e:
            self.logger.error(f"Error building order: {e}")
            return {"error": str(e)}
    
    def _calculate_expiry_date(self, dte: int) -> datetime:
        """Calculate expiration date from DTE."""
        from datetime import timedelta
        return datetime.now() + timedelta(days=dte)
    
    # =========================================================================
    # ORDER ESTIMATION
    # =========================================================================
    
    def estimate_order_cost(
        self,
        bid_price: float,
        ask_price: float,
        contracts: int,
        side: str = "buy"
    ) -> Dict:
        """
        Estimate order cost including slippage.
        
        Args:
            bid_price: Bid price
            ask_price: Ask price
            contracts: Number of contracts
            side: "buy" or "sell"
        
        Returns:
            Dict with cost estimates
        """
        
        # Use mid-price for estimation
        mid_price = (bid_price + ask_price) / 2
        
        # Assume some slippage (1/2 of the spread)
        if side.lower() == "buy":
            fill_price = ask_price  # Buy at ask
        else:
            fill_price = bid_price  # Sell at bid
        
        total_cost = fill_price * contracts * 100
        
        # Slippage estimate (1/2 of spread)
        spread = ask_price - bid_price
        slippage = (spread / 2) * contracts * 100
        
        return {
            "bid": bid_price,
            "ask": ask_price,
            "mid": mid_price,
            "estimated_fill": fill_price,
            "estimated_cost": total_cost,
            "estimated_slippage": slippage,
            "total_with_slippage": total_cost + slippage,
        }
