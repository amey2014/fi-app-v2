"""
core/decision_engine.py - Trading decision engine
Makes trading decisions based on technical analysis and risk management
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
logger = logging.getLogger(__name__)
class DecisionEngine:
    """
    Makes trading decisions based on technical signals and risk rules.
    Works with PaperTrader for simulation or RealTrader for live trading.
    """
    
    def __init__(self, trader, risk_manager, max_concurrent_trades: int = 5):
        """
        Initialize decision engine.
        
        Args:
            trader: TradeManager (PaperTrader or RealTrader)
            risk_manager: RiskManager instance
            max_concurrent_trades: Maximum concurrent positions
        """
        self.trader = trader
        self.risk_manager = risk_manager
        self.max_concurrent_trades = max_concurrent_trades
        self.last_trade_time = {}  # {symbol: datetime}
        self.cooldown_minutes = 30
        
        logger.info("[DECISION ENGINE] Initialized")
    
    def should_trade(self, symbol: str, signal: Dict, current_price: float) -> Tuple[bool, str]:
        """
        Determine if trade should be placed.
        
        Args:
            symbol: Stock symbol
            signal: Technical signal data
            current_price: Current price
        
        Returns:
            (should_trade: bool, reason: str)
        """
        
        # Check signal strength
        if signal['confidence'] < 40:
            return False, "Signal confidence too low"
        
        # Check if already has position
        if symbol in self.trader.open_positions:
            return False, "Position already open"
        
        # Check concurrent trades limit
        if len(self.trader.open_positions) >= self.max_concurrent_trades:
            return False, "Max concurrent trades reached"
        
        # Check cooldown period
        if symbol in self.last_trade_time:
            time_since_last = (datetime.now() - self.last_trade_time[symbol]).total_seconds() / 60
            if time_since_last < self.cooldown_minutes:
                return False, f"Cooldown period active ({time_since_last:.0f}m)"
        
        # Check daily loss limit
        account = self.trader.get_account_summary()
        if account['daily_pnl'] < -account['initial_capital'] * 0.12:  # 12% daily loss limit
            return False, "Daily loss limit exceeded"
        
        # Check capital availability
        if account['current_balance'] <= account['initial_capital'] * 0.2:  # Keep 20% buffer
            return False, "Insufficient capital"
        
        return True, "All checks passed"
    
    def calculate_trade_parameters(self, symbol: str, signal: Dict, 
                                  current_price: float) -> Optional[Dict]:
        """
        Calculate trade parameters (size, stop-loss, take-profit).
        
        Args:
            symbol: Stock symbol
            signal: Technical signal
            current_price: Current price
        
        Returns:
            Trade parameters or None
        """
        
        # Get risk parameters
        risk_params = self.risk_manager.calculate_position_size(
            symbol, current_price
        )
        
        if not risk_params:
            logger.warning(f"Could not calculate risk params for {symbol}")
            return None
        
        parameters = {
            'symbol': symbol,
            'side': 'BUY' if signal['signal'] == 'BUY' else 'SELL',
            'quantity': risk_params['quantity'],
            'entry_price': current_price,
            'stop_loss': risk_params['stop_loss'],
            'take_profit': risk_params['take_profit'],
            'max_risk': risk_params['max_risk'],
            'max_reward': risk_params['max_reward'],
            'risk_reward_ratio': risk_params.get('risk_reward_ratio', 1.0),
            'signal_data': signal,
        }
        
        return parameters
    
    def evaluate_trade_signal(self, symbol: str, signal: Dict, 
                            current_price: float) -> Optional[Dict]:
        """
        Full evaluation of whether to place a trade.
        
        Args:
            symbol: Stock symbol
            signal: Technical signal
            current_price: Current price
        
        Returns:
            Trade parameters if approved, None otherwise
        """
        
        # 1. Check if trade is allowed
        should_trade, reason = self.should_trade(symbol, signal, current_price)
        if not should_trade:
            logger.debug(f"[DECISION ENGINE] {symbol}: {reason}")
            return None
        
        # 2. Calculate trade parameters
        trade_params = self.calculate_trade_parameters(symbol, signal, current_price)
        if not trade_params:
            return None
        
        # 3. Validate risk/reward
        if trade_params['risk_reward_ratio'] < 1.0:
            logger.warning(f"[DECISION ENGINE] {symbol}: Poor risk/reward ratio")
            return None
        
        logger.info(
            f"[DECISION ENGINE] APPROVED {symbol}: "
            f"{trade_params['side']} {trade_params['quantity']} @ ${current_price:.2f}"
        )
        
        return trade_params
    
    def execute_trade(self, trade_params: Dict) -> bool:
        """
        Execute approved trade.
        
        Args:
            trade_params: Trade parameters from evaluate_trade_signal()
        
        Returns:
            True if trade opened successfully
        """
        
        symbol = trade_params['symbol']
        
        # Open position with PaperTrader
        position = self.trader.open_position(
            symbol=symbol,
            side=trade_params['side'],
            quantity=trade_params['quantity'],
            entry_price=trade_params['entry_price'],
            stop_loss=trade_params['stop_loss'],
            take_profit=trade_params['take_profit'],
            signal_data=trade_params['signal_data'],
        )
        
        if position:
            self.last_trade_time[symbol] = datetime.now()
            return True
        else:
            logger.error(f"[DECISION ENGINE] Failed to open position for {symbol}")
            return False