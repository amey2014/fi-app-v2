"""
core/paper_trader.py - Paper Trading Simulator
Simulates trades without actually placing orders on Alpaca
Allows testing trading logic before live trading
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
logger = logging.getLogger(__name__)
class PaperTrader:
    """
    Simulates trading activity without placing real orders.
    Useful for backtesting and validating trading logic.
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize paper trading simulator.
        
        Args:
            initial_capital: Starting account balance
        """
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.open_positions = {}  # {symbol: position_data}
        self.closed_trades = []   # List of completed trades
        self.trade_history = []   # All trades (open + closed)
        self.daily_pnl = 0
        self.total_pnl = 0
        
        logger.info(f"[PAPER TRADER] Initialized with ${initial_capital:,.2f}")
    
    # =========================================================================
    # POSITION MANAGEMENT
    # =========================================================================
    
    def open_position(self, symbol: str, side: str, quantity: int, 
                     entry_price: float, stop_loss: float, 
                     take_profit: float, signal_data: Dict) -> Dict:
        """
        Simulate opening a position (BUY or SELL).
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            side: 'BUY' or 'SELL'
            quantity: Number of shares
            entry_price: Entry price per share
            stop_loss: Stop-loss price level
            take_profit: Take-profit price level
            signal_data: Technical signal data that triggered trade
        
        Returns:
            Position data dictionary
        """
        
        # Check if position already exists
        if symbol in self.open_positions:
            logger.warning(f"[PAPER TRADER] Position already open for {symbol}")
            return None
        
        # Calculate trade details
        trade_value = quantity * entry_price
        max_loss = quantity * abs(entry_price - stop_loss)
        max_gain = quantity * abs(take_profit - entry_price)
        
        # Check capital availability
        if side == 'BUY' and trade_value > self.current_balance:
            logger.error(f"[PAPER TRADER] Insufficient capital for {symbol}")
            return None
        
        # Create position record
        position = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'max_loss': max_loss,
            'max_gain': max_gain,
            'current_price': entry_price,
            'unrealized_pnl': 0,
            'unrealized_pnl_pct': 0,
            'signal_data': signal_data,
            'status': 'OPEN',
            'trade_id': len(self.trade_history) + 1,
        }
        
        # Update balance (deduct for BUY, add for SELL)
        if side == 'BUY':
            self.current_balance -= trade_value
        else:
            self.current_balance += trade_value
        
        # Store position
        self.open_positions[symbol] = position
        self.trade_history.append(position)
        
        logger.info(
            f"[PAPER TRADER] OPENED {side} {symbol}: "
            f"{quantity} @ ${entry_price:.2f} | "
            f"SL: ${stop_loss:.2f} | TP: ${take_profit:.2f} | "
            f"Risk: ${max_loss:.2f} | Reward: ${max_gain:.2f}"
        )
        
        return position
    
    def update_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Update position P&L based on current price.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        
        Returns:
            Updated position or None
        """
        
        if symbol not in self.open_positions:
            return None
        
        position = self.open_positions[symbol]
        
        # Calculate P&L
        if position['side'] == 'BUY':
            unrealized_pnl = position['quantity'] * (current_price - position['entry_price'])
        else:  # SELL
            unrealized_pnl = position['quantity'] * (position['entry_price'] - current_price)
        
        unrealized_pnl_pct = (unrealized_pnl / (position['quantity'] * position['entry_price'])) * 100
        
        # Update position
        position['current_price'] = current_price
        position['unrealized_pnl'] = unrealized_pnl
        position['unrealized_pnl_pct'] = unrealized_pnl_pct
        
        return position
    
    def close_position(self, symbol: str, exit_price: float, 
                      reason: str = 'MANUAL') -> Optional[Dict]:
        """
        Simulate closing a position.
        
        Args:
            symbol: Stock symbol
            exit_price: Exit price per share
            reason: Reason for exit (STOP_LOSS, TAKE_PROFIT, TIME_EXIT, etc.)
        
        Returns:
            Closed trade data
        """
        
        if symbol not in self.open_positions:
            logger.warning(f"[PAPER TRADER] No open position for {symbol}")
            return None
        
        position = self.open_positions[symbol]
        
        # Calculate realized P&L
        if position['side'] == 'BUY':
            realized_pnl = position['quantity'] * (exit_price - position['entry_price'])
        else:  # SELL
            realized_pnl = position['quantity'] * (position['entry_price'] - exit_price)
        
        realized_pnl_pct = (realized_pnl / (position['quantity'] * position['entry_price'])) * 100
        
        # Update balance
        exit_value = position['quantity'] * exit_price
        if position['side'] == 'BUY':
            self.current_balance += exit_value
        else:
            self.current_balance -= exit_value
        
        # Create closed trade record
        closed_trade = {
            'symbol': symbol,
            'side': position['side'],
            'quantity': position['quantity'],
            'entry_price': position['entry_price'],
            'entry_time': position['entry_time'],
            'exit_price': exit_price,
            'exit_time': datetime.now(),
            'duration': (datetime.now() - position['entry_time']).total_seconds() / 60,  # minutes
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'realized_pnl': realized_pnl,
            'realized_pnl_pct': realized_pnl_pct,
            'reason': reason,
            'trade_id': position['trade_id'],
            'status': 'CLOSED',
            'signal_data': position['signal_data'],
        }
        
        # Update tracking
        self.closed_trades.append(closed_trade)
        self.total_pnl += realized_pnl
        self.daily_pnl += realized_pnl
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        # Determine win/loss
        win_loss = "WIN" if realized_pnl > 0 else ("LOSS" if realized_pnl < 0 else "BREAK_EVEN")
        
        logger.info(
            f"[PAPER TRADER] CLOSED {position['side']} {symbol}: "
            f"${exit_price:.2f} | "
            f"P&L: ${realized_pnl:.2f} ({realized_pnl_pct:+.2f}%) [{win_loss}] | "
            f"Reason: {reason} | "
            f"Duration: {closed_trade['duration']:.0f}m"
        )
        
        return closed_trade
    
    # =========================================================================
    # MONITORING & CHECKING
    # =========================================================================
    
    def check_exit_conditions(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check if position should be exited (stop-loss, take-profit, etc.).
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        
        Returns:
            Exit reason or None
        """
        
        if symbol not in self.open_positions:
            return None
        
        position = self.open_positions[symbol]
        
        # Check stop-loss
        if position['side'] == 'BUY':
            if current_price <= position['stop_loss']:
                return "STOP_LOSS"
            if current_price >= position['take_profit']:
                return "TAKE_PROFIT"
        else:  # SELL
            if current_price >= position['stop_loss']:
                return "STOP_LOSS"
            if current_price <= position['take_profit']:
                return "TAKE_PROFIT"
        
        return None
    
    def check_time_exit(self, symbol: str, max_hold_minutes: int = 120) -> bool:
        """
        Check if position exceeded max hold time.
        
        Args:
            symbol: Stock symbol
            max_hold_minutes: Maximum hold time in minutes
        
        Returns:
            True if should exit based on time
        """
        
        if symbol not in self.open_positions:
            return False
        
        position = self.open_positions[symbol]
        hold_time = (datetime.now() - position['entry_time']).total_seconds() / 60
        
        return hold_time >= max_hold_minutes
    
    def get_open_positions(self) -> Dict:
        """Get all open positions."""
        return self.open_positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get specific position."""
        return self.open_positions.get(symbol)
    
    # =========================================================================
    # ACCOUNT METRICS
    # =========================================================================
    
    def get_account_summary(self) -> Dict:
        """
        Get account summary with all metrics.
        
        Returns:
            Dictionary with account metrics
        """
        
        # Calculate total unrealized P&L
        total_unrealized_pnl = sum(
            pos['unrealized_pnl'] 
            for pos in self.open_positions.values()
        )
        
        # Calculate portfolio value
        portfolio_value = self.current_balance + total_unrealized_pnl
        
        # Calculate metrics
        trades_total = len(self.closed_trades)
        if trades_total > 0:
            winning_trades = sum(1 for t in self.closed_trades if t['realized_pnl'] > 0)
            losing_trades = sum(1 for t in self.closed_trades if t['realized_pnl'] < 0)
            win_rate = (winning_trades / trades_total) * 100
            
            avg_win = (sum(t['realized_pnl'] for t in self.closed_trades if t['realized_pnl'] > 0) 
                      / winning_trades if winning_trades > 0 else 0)
            avg_loss = (sum(t['realized_pnl'] for t in self.closed_trades if t['realized_pnl'] < 0) 
                       / losing_trades if losing_trades > 0 else 0)
            
            largest_win = max((t['realized_pnl'] for t in self.closed_trades), default=0)
            largest_loss = min((t['realized_pnl'] for t in self.closed_trades), default=0)
        else:
            win_rate = 0
            winning_trades = 0
            losing_trades = 0
            avg_win = 0
            avg_loss = 0
            largest_win = 0
            largest_loss = 0
        
        return {
            'initial_capital': self.initial_capital,
            'current_balance': self.current_balance,
            'portfolio_value': portfolio_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'return_pct': ((portfolio_value - self.initial_capital) / self.initial_capital) * 100,
            'open_positions_count': len(self.open_positions),
            'total_trades': trades_total,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        }
    
    def print_account_summary(self):
        """Print formatted account summary."""
        summary = self.get_account_summary()
        
        print("\n" + "="*70)
        print("PAPER TRADING ACCOUNT SUMMARY")
        print("="*70)
        print(f"\nCapital:")
        print(f"  Initial: ${summary['initial_capital']:,.2f}")
        print(f"  Current: ${summary['current_balance']:,.2f}")
        print(f"  Portfolio Value: ${summary['portfolio_value']:,.2f}")
        
        print(f"\nP&L:")
        print(f"  Realized: ${summary['total_realized_pnl']:+,.2f}")
        print(f"  Unrealized: ${summary['total_unrealized_pnl']:+,.2f}")
        print(f"  Daily: ${summary['daily_pnl']:+,.2f}")
        print(f"  Return: {summary['return_pct']:+.2f}%")
        
        print(f"\nPositions:")
        print(f"  Open: {summary['open_positions_count']}")
        print(f"  Total Trades: {summary['total_trades']}")
        
        if summary['total_trades'] > 0:
            print(f"\nPerformance:")
            print(f"  Wins: {summary['winning_trades']} | Losses: {summary['losing_trades']}")
            print(f"  Win Rate: {summary['win_rate']:.1f}%")
            print(f"  Avg Win: ${summary['avg_win']:,.2f}")
            print(f"  Avg Loss: ${summary['avg_loss']:,.2f}")
            print(f"  Largest Win: ${summary['largest_win']:,.2f}")
            print(f"  Largest Loss: ${summary['largest_loss']:,.2f}")
            print(f"  Profit Factor: {summary['profit_factor']:.2f}")
        
        print("\n" + "="*70)
    
    def print_open_positions(self):
        """Print all open positions."""
        if not self.open_positions:
            print("\nNo open positions")
            return
        
        print("\n" + "="*70)
        print("OPEN POSITIONS")
        print("="*70)
        
        for symbol, position in self.open_positions.items():
            print(f"\n{symbol} ({position['side']})")
            print(f"  Qty: {position['quantity']} @ ${position['entry_price']:.2f}")
            print(f"  Current: ${position['current_price']:.2f}")
            print(f"  P&L: ${position['unrealized_pnl']:+.2f} ({position['unrealized_pnl_pct']:+.2f}%)")
            print(f"  SL: ${position['stop_loss']:.2f} | TP: ${position['take_profit']:.2f}")
            print(f"  Entry: {position['entry_time'].strftime('%H:%M:%S')}")
        
        print("\n" + "="*70)
    
    def print_closed_trades(self, limit: int = 10):
        """Print recent closed trades."""
        if not self.closed_trades:
            print("\nNo closed trades")
            return
        
        print("\n" + "="*70)
        print(f"RECENT CLOSED TRADES (Last {limit})")
        print("="*70)
        
        for trade in self.closed_trades[-limit:]:
            win_loss = "WIN" if trade['realized_pnl'] > 0 else ("LOSS" if trade['realized_pnl'] < 0 else "BE")
            print(
                f"{trade['symbol']} {trade['side']:4s} | "
                f"${trade['entry_price']:7.2f} → ${trade['exit_price']:7.2f} | "
                f"{trade['realized_pnl']:+8.2f} ({trade['realized_pnl_pct']:+6.2f}%) [{win_loss}] | "
                f"{trade['reason']} | {trade['duration']:.0f}m"
            )
        
        print("="*70)
    
    # =========================================================================
    # RESET
    # =========================================================================
    
    def reset_daily(self):
        """Reset daily metrics (called at market close)."""
        self.daily_pnl = 0
        logger.info("[PAPER TRADER] Daily metrics reset")
    
    def reset_all(self):
        """Reset entire trading session."""
        self.current_balance = self.initial_capital
        self.open_positions.clear()
        self.closed_trades.clear()
        self.trade_history.clear()
        self.daily_pnl = 0
        self.total_pnl = 0
        logger.info("[PAPER TRADER] All metrics reset")
