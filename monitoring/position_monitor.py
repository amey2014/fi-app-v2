"""
monitoring/position_monitor.py - Real-time position tracking and analysis
Monitors open positions and triggers exit conditions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config.logger import logger
from config.settings import TradingConfig
from utils.helpers import parse_option_symbol

class PositionMonitor:
    """Monitor open positions in real-time."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
        self.peak_prices = {}  # Track peak price for trailing stops
    
    # =========================================================================
    # POSITION ANALYSIS
    # =========================================================================
    
    def analyze_position(
        self,
        position: Dict,
        current_price: float,
        current_time: datetime = None
    ) -> Dict:
        """
        Analyze a single open position.
        
        Args:
            position: Position dict from Alpaca
            current_price: Current option price
            current_time: Current time (for DTE calculation)
        
        Returns:
            Dict with position analysis
        """
        
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Parse option symbol
            symbol = position.get("symbol", "")
            parsed = parse_option_symbol(symbol)
            
            if "error" in parsed:
                self.logger.warning(f"Could not parse symbol: {symbol}")
                return {"error": f"Invalid symbol: {symbol}"}
            
            # Extract position info
            entry_price = float(position.get("avg_entry_price", 0))
            qty = int(position.get("qty", 0))
            
            # Calculate P&L
            unrealized_pl = float(position.get("unrealized_pl", 0))
            unrealized_pl_pct = float(position.get("unrealized_plpc", 0)) * 100
            
            # DTE calculation
            dte = parsed.get("dte", 0)
            
            # Update peak price for trailing stop
            peak_price = self.peak_prices.get(symbol, current_price)
            if current_price > peak_price:
                peak_price = current_price
                self.peak_prices[symbol] = current_price
            
            # Calculate trailing stop
            trailing_stop = peak_price * (1 + self.config.TRAILING_STOP_PCT / 100)
            
            return {
                "symbol": symbol,
                "ticker": parsed.get("ticker"),
                "option_type": parsed.get("option_type"),
                "strike": parsed.get("strike"),
                "dte": dte,
                "entry_price": entry_price,
                "current_price": current_price,
                "qty": qty,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_pct": unrealized_pl_pct,
                "peak_price": peak_price,
                "trailing_stop": trailing_stop,
                "position_cost": entry_price * qty * 100,
                "current_value": current_price * qty * 100,
                "timestamp": current_time.isoformat(),
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing position: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # EXIT CONDITION CHECKING
    # =========================================================================
    
    def check_exit_conditions(
        self,
        position_analysis: Dict,
        historical_trades: List[Dict] = None
    ) -> Dict:
        """
        Check all exit conditions for a position.
        
        Returns exit signal if condition met, otherwise None.
        
        Args:
            position_analysis: Position analysis dict
            historical_trades: List of closed trades (for context)
        
        Returns:
            Dict with exit condition details
        """
        
        if "error" in position_analysis:
            return None
        
        try:
            symbol = position_analysis.get("symbol")
            dte = position_analysis.get("dte", 0)
            unrealized_pl_pct = position_analysis.get("unrealized_pl_pct", 0)
            current_price = position_analysis.get("current_price", 0)
            trailing_stop = position_analysis.get("trailing_stop", 0)
            
            # EXIT 1: Stop Loss (Hard -30%)
            if unrealized_pl_pct <= self.config.STOP_LOSS_PCT:
                return {
                    "should_exit": True,
                    "exit_reason": "stop_loss",
                    "trigger": f"Hard stop at {self.config.STOP_LOSS_PCT}%",
                    "exit_price": current_price,
                    "pnl_pct": unrealized_pl_pct,
                    "exit_type": "MARKET",
                    "severity": "HIGH",
                }
            
            # EXIT 2: Trailing Stop
            if current_price <= trailing_stop:
                return {
                    "should_exit": True,
                    "exit_reason": "trailing_stop",
                    "trigger": f"Trailing stop hit (${trailing_stop:.2f})",
                    "exit_price": current_price,
                    "pnl_pct": unrealized_pl_pct,
                    "exit_type": "MARKET",
                    "severity": "MEDIUM",
                }
            
            # EXIT 3: DTE Threshold (< 5 days)
            if dte < self.config.MIN_DTE_AUTO_EXIT:
                return {
                    "should_exit": True,
                    "exit_reason": "dte_threshold",
                    "trigger": f"DTE below {self.config.MIN_DTE_AUTO_EXIT} days ({dte} days)",
                    "exit_price": current_price,
                    "pnl_pct": unrealized_pl_pct,
                    "exit_type": "MARKET",
                    "severity": "MEDIUM",
                }
            
            # EXIT 4: Profit Taking (Dynamic targets)
            profit_targets = self._get_profit_targets(position_analysis, historical_trades)
            
            for idx, target in enumerate(profit_targets):
                if unrealized_pl_pct >= target["pct"]:
                    return {
                        "should_exit": True,
                        "exit_reason": f"profit_target_{idx + 1}",
                        "trigger": f"Target {idx + 1}: {target['pct']}% reached",
                        "exit_price": current_price,
                        "pnl_pct": unrealized_pl_pct,
                        "exit_quantity": int(position_analysis.get("qty", 0) * target["portion"]),
                        "remaining_quantity": int(position_analysis.get("qty", 0) * (1 - target["portion"])),
                        "exit_type": target["type"],
                        "severity": "LOW",
                    }
            
            # No exit condition met
            return None
        
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return None
    
    def _get_profit_targets(
        self,
        position_analysis: Dict,
        historical_trades: List[Dict] = None
    ) -> List[Dict]:
        """
        Get dynamic profit targets based on position characteristics.
        
        Returns list of targets with trigger percentages and allocation %.
        """
        
        dte = position_analysis.get("dte", 30)
        
        # Base targets (can be overridden based on strategy)
        if dte < 14:
            # Short DTE: aggressive targets
            targets = [
                {"pct": 15, "portion": 0.50, "type": "PARTIAL"},  # Sell 50% at 15%
                {"pct": 25, "portion": 0.30, "type": "PARTIAL"},  # Sell 30% at 25%
                {"pct": 50, "portion": 1.00, "type": "FULL"},     # Sell remaining at 50%
            ]
        elif dte < 30:
            # Medium DTE
            targets = [
                {"pct": 20, "portion": 0.50, "type": "PARTIAL"},
                {"pct": 40, "portion": 0.30, "type": "PARTIAL"},
                {"pct": 80, "portion": 1.00, "type": "FULL"},
            ]
        else:
            # Long DTE: conservative targets
            targets = [
                {"pct": 25, "portion": 0.50, "type": "PARTIAL"},
                {"pct": 50, "portion": 0.30, "type": "PARTIAL"},
                {"pct": 100, "portion": 1.00, "type": "FULL"},
            ]
        
        return targets
    
    # =========================================================================
    # POSITION MONITORING UTILITIES
    # =========================================================================
    
    def calculate_portfolio_greeks(self, positions: List[Dict]) -> Dict:
        """
        Calculate aggregate Greeks for entire portfolio.
        
        Args:
            positions: List of position dicts with Greeks
        
        Returns:
            Dict with portfolio Greek totals
        """
        
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        
        for pos in positions:
            try:
                delta = float(pos.get("delta", 0)) * pos.get("qty", 0)
                gamma = float(pos.get("gamma", 0)) * pos.get("qty", 0)
                theta = float(pos.get("theta", 0)) * pos.get("qty", 0)
                vega = float(pos.get("vega", 0)) * pos.get("qty", 0)
                
                total_delta += delta
                total_gamma += gamma
                total_theta += theta
                total_vega += vega
            except:
                continue
        
        return {
            "portfolio_delta": round(total_delta, 2),
            "portfolio_gamma": round(total_gamma, 4),
            "portfolio_theta": round(total_theta, 4),
            "portfolio_vega": round(total_vega, 4),
        }
    
    def get_position_summary(self, positions: List[Dict]) -> Dict:
        """
        Get summary statistics for all open positions.
        
        Args:
            positions: List of analyzed positions
        
        Returns:
            Dict with summary metrics
        """
        
        if not positions:
            return {
                "total_positions": 0,
                "total_capital_deployed": 0,
                "total_unrealized_pl": 0,
                "total_unrealized_pl_pct": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "average_dte": 0,
            }
        
        # Filter valid positions
        valid_positions = [p for p in positions if "error" not in p]
        
        if not valid_positions:
            return {"error": "No valid positions"}
        
        total_pl = sum([p.get("unrealized_pl", 0) for p in valid_positions])
        total_cost = sum([p.get("position_cost", 0) for p in valid_positions])
        total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
        
        winners = [p for p in valid_positions if p.get("unrealized_pl_pct", 0) > 0]
        losers = [p for p in valid_positions if p.get("unrealized_pl_pct", 0) <= 0]
        
        avg_dte = np.mean([p.get("dte", 30) for p in valid_positions])
        
        return {
            "total_positions": len(valid_positions),
            "total_capital_deployed": round(total_cost, 2),
            "total_unrealized_pl": round(total_pl, 2),
            "total_unrealized_pl_pct": round(total_pl_pct, 2),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": round(len(winners) / len(valid_positions) * 100, 1) if valid_positions else 0,
            "average_dte": round(avg_dte, 0),
            "positions": valid_positions,
        }
