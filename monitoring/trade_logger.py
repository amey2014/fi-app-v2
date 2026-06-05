"""
monitoring/trade_logger.py - Trade logging and history management
Logs all trade events and maintains trade history
"""

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from config.logger import logger

class TradeLogger:
    """Log and manage trade history."""
    
    def __init__(self, log_dir: str = "logs"):
        self.logger = logger
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.trades_file = self.log_dir / "trades.json"
        self.entries_file = self.log_dir / "entries.json"
        self.exits_file = self.log_dir / "exits.json"
        self.trades = self._load_trades()
    
    # =========================================================================
    # TRADE LOGGING
    # =========================================================================
    
    def log_entry(self, entry_data: Dict) -> Dict:
        """
        Log a new trade entry.
        
        Args:
            entry_data: Entry details
        
        Returns:
            Entry dict with ID
        """
        
        try:
            entry = {
                "trade_id": entry_data.get("trade_id"),
                "timestamp": datetime.now().isoformat(),
                "event": "ENTRY",
                "ticker": entry_data.get("ticker"),
                "option_type": entry_data.get("option_type"),
                "strike": entry_data.get("strike"),
                "dte": entry_data.get("dte"),
                "entry_price": entry_data.get("entry_price"),
                "contracts": entry_data.get("contracts"),
                "position_cost": entry_data.get("position_cost"),
                
                # Market context
                "rsi": entry_data.get("rsi"),
                "iv": entry_data.get("iv"),
                "iv_percentile": entry_data.get("iv_percentile"),
                "vix": entry_data.get("vix"),
                "stock_price": entry_data.get("stock_price"),
                
                # Decision details
                "confidence": entry_data.get("confidence"),
                "reason": entry_data.get("reason"),
            }
            
            # Save to trades list
            self.trades.append(entry)
            self._save_trades()
            
            self.logger.info(
                f"Entry logged: {entry['ticker']} {entry['option_type']} "
                f"\${entry['strike']} - ${entry['entry_price']} x{entry['contracts']}"
            )
            
            return entry
        
        except Exception as e:
            self.logger.error(f"Error logging entry: {e}")
            return {"error": str(e)}
    
    def log_exit(self, exit_data: Dict) -> Dict:
        """
        Log a trade exit.
        
        Args:
            exit_data: Exit details
        
        Returns:
            Exit dict
        """
        
        try:
            exit_record = {
                "trade_id": exit_data.get("trade_id"),
                "timestamp": datetime.now().isoformat(),
                "event": "EXIT",
                "ticker": exit_data.get("ticker"),
                "exit_reason": exit_data.get("exit_reason"),
                "exit_trigger": exit_data.get("exit_trigger"),
                "exit_price": exit_data.get("exit_price"),
                "exit_qty": exit_data.get("exit_qty"),
                "pnl_dollars": exit_data.get("pnl_dollars"),
                "pnl_pct": exit_data.get("pnl_pct"),
            }
            
            # Update trades list
            self.trades.append(exit_record)
            self._save_trades()
            
            self.logger.info(
                f"Exit logged: {exit_record['ticker']} - "
                f"Reason: {exit_record['exit_reason']} - "
                f"P&L: {exit_record['pnl_pct']:+.2f}%"
            )
            
            return exit_record
        
        except Exception as e:
            self.logger.error(f"Error logging exit: {e}")
            return {"error": str(e)}
    
    def log_closed_trade(self, trade_record: Dict) -> Dict:
        """
        Log a fully closed trade record.
        
        Args:
            trade_record: Complete trade record
        
        Returns:
            Logged trade record
        """
        
        try:
            trade = {
                "trade_id": trade_record.get("trade_id"),
                "timestamp": datetime.now().isoformat(),
                "event": "TRADE_CLOSED",
                "ticker": trade_record.get("ticker"),
                "option_type": trade_record.get("option_type"),
                "strike": trade_record.get("strike"),
                "entry_time": trade_record.get("entry_time"),
                "exit_time": trade_record.get("exit_time"),
                "hold_days": trade_record.get("hold_days"),
                "entry_price": trade_record.get("entry_price"),
                "exit_price": trade_record.get("exit_price"),
                "pnl_dollars": trade_record.get("pnl_dollars"),
                "pnl_pct": trade_record.get("pnl_pct"),
                "exit_reason": trade_record.get("exit_reason"),
                "profitable": trade_record.get("profitable"),
            }
            
            self.trades.append(trade)
            self._save_trades()
            
            self.logger.info(
                f"Trade closed: {trade['ticker']} - "
                f"Hold: {trade['hold_days']}d - "
                f"P&L: {trade['pnl_pct']:+.2f}% (${trade['pnl_dollars']:+.2f})"
            )
            
            return trade
        
        except Exception as e:
            self.logger.error(f"Error logging closed trade: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # TRADE RETRIEVAL & FILTERING
    # =========================================================================
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trade records."""
        return self.trades[-limit:]
    
    def get_trades_by_ticker(self, ticker: str) -> List[Dict]:
        """Get all trades for a specific ticker."""
        return [t for t in self.trades if t.get("ticker") == ticker]
    
    def get_closed_trades(self) -> List[Dict]:
        """Get all closed trade records."""
        return [t for t in self.trades if t.get("event") == "TRADE_CLOSED"]
    
    def get_trades_by_date(self, date_str: str) -> List[Dict]:
        """Get trades for a specific date (YYYY-MM-DD)."""
        return [t for t in self.trades if t.get("timestamp", "").startswith(date_str)]
    
    def get_winning_trades(self) -> List[Dict]:
        """Get all profitable trades."""
        return [t for t in self.trades if t.get("event") == "TRADE_CLOSED" and t.get("profitable")]
    
    def get_losing_trades(self) -> List[Dict]:
        """Get all losing trades."""
        return [t for t in self.trades if t.get("event") == "TRADE_CLOSED" and not t.get("profitable")]
    
    # =========================================================================
    # PERFORMANCE ANALYTICS
    # =========================================================================
    
    def calculate_performance_stats(self) -> Dict:
        """Calculate performance statistics."""
        
        closed_trades = self.get_closed_trades()
        
        if not closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl_per_trade": 0,
            }
        
        winning = [t for t in closed_trades if t.get("profitable")]
        losing = [t for t in closed_trades if not t.get("profitable")]
        
        total_pnl = sum([t.get("pnl_dollars", 0) for t in closed_trades])
        
        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate_pct": len(winning) / len(closed_trades) * 100,
            "total_pnl_dollars": round(total_pnl, 2),
            "avg_pnl_per_trade": round(total_pnl / len(closed_trades), 2),
            "avg_win_pct": round(sum([t.get("pnl_pct", 0) for t in winning]) / len(winning), 2) if winning else 0,
            "avg_loss_pct": round(sum([t.get("pnl_pct", 0) for t in losing]) / len(losing), 2) if losing else 0,
            "best_trade_pnl": max([t.get("pnl_pct", 0) for t in closed_trades]),
            "worst_trade_pnl": min([t.get("pnl_pct", 0) for t in closed_trades]),
            "avg_hold_days": round(sum([t.get("hold_days", 0) for t in closed_trades]) / len(closed_trades), 1),
        }
    
    # =========================================================================
    # FILE I/O
    # =========================================================================
    
    def _load_trades(self) -> List[Dict]:
        """Load trades from file."""
        
        try:
            if self.trades_file.exists():
                with open(self.trades_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.warning(f"Error loading trades file: {e}")
            return []
    
    def _save_trades(self):
        """Save trades to file."""
        
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving trades file: {e}")
    
    def export_to_csv(self, filepath: str = None) -> str:
        """
        Export closed trades to CSV.
        
        Args:
            filepath: Output CSV path
        
        Returns:
            Path to exported file
        """
        
        if filepath is None:
            filepath = self.log_dir / "closed_trades.csv"
        
        try:
            closed_trades = self.get_closed_trades()
            
            if not closed_trades:
                self.logger.warning("No closed trades to export")
                return ""
            
            df = pd.DataFrame(closed_trades)
            df.to_csv(filepath, index=False)
            
            self.logger.info(f"Exported {len(closed_trades)} trades to {filepath}")
            return str(filepath)
        
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return ""
    
    def get_trade_by_id(self, trade_id: str) -> Optional[Dict]:
        """Get specific trade by ID."""
        
        trades = [t for t in self.trades if t.get("trade_id") == trade_id]
        return trades[0] if trades else None
