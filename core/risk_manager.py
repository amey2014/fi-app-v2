"""
core/risk_manager.py - Risk management module
Calculates position sizing, stop-loss, take-profit levels
"""
import logging
from typing import Dict, Optional
import pandas as pd
logger = logging.getLogger(__name__)
class RiskManager:
    """Manages position sizing and risk parameters."""
    
    def __init__(self, 
                 risk_per_trade: float = 0.01,      # 1% per trade
                 daily_loss_limit: float = 0.12,    # 12% daily loss limit
                 max_concurrent_trades: int = 5,
                 min_risk_reward: float = 1.5):     # 1:1.5 minimum ratio
        """
        Initialize risk manager.
        
        Args:
            risk_per_trade: Max risk per trade as % of capital
            daily_loss_limit: Max daily loss as % of capital
            max_concurrent_trades: Max open positions
            min_risk_reward: Minimum risk/reward ratio
        """
        self.risk_per_trade = risk_per_trade
        self.daily_loss_limit = daily_loss_limit
        self.max_concurrent_trades = max_concurrent_trades
        self.min_risk_reward = min_risk_reward
        
        logger.info(
            f"[RISK MANAGER] Initialized: "
            f"Risk/Trade={risk_per_trade*100}%, "
            f"Daily Loss Limit={daily_loss_limit*100}%, "
            f"Max Trades={max_concurrent_trades}"
        )
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               atr: float = None, capital: float = 100000) -> Optional[Dict]:
        """
        Calculate position size based on risk parameters.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            atr: Average True Range (for stop-loss calculation)
            capital: Available capital
        
        Returns:
            Dict with position parameters or None
        """
        
        # Default ATR if not provided (use 2% of price)
        if atr is None:
            atr = entry_price * 0.02
        
        # Calculate stop-loss and take-profit
        stop_loss = entry_price - (2 * atr)  # 2 ATR below entry
        take_profit = entry_price + (3 * atr)  # 3 ATR above entry
        
        # Calculate max loss per trade
        max_loss_per_trade = capital * self.risk_per_trade
        
        # Calculate quantity based on max loss
        stop_distance = entry_price - stop_loss
        quantity = int(max_loss_per_trade / stop_distance) if stop_distance > 0 else 0
        
        if quantity <= 0:
            logger.warning(f"[RISK MGR] Invalid position size for {symbol}")
            return None
        
        # Calculate risk and reward
        max_risk = quantity * stop_distance
        max_reward = quantity * (take_profit - entry_price)
        risk_reward_ratio = max_reward / max_risk if max_risk > 0 else 0
        
        # Check minimum risk/reward
        if risk_reward_ratio < self.min_risk_reward:
            logger.warning(
                f"[RISK MGR] {symbol}: Poor R/R ratio ({risk_reward_ratio:.2f} < {self.min_risk_reward})"
            )
            return None
        
        return {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'max_risk': max_risk,
            'max_reward': max_reward,
            'risk_reward_ratio': risk_reward_ratio,
        }