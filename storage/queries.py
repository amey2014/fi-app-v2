"""
storage/queries.py - Pre-built database queries and reports
Convenience functions for common queries
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from storage.database import Database

class Queries:
    """Pre-built queries for common operations."""
    
    def __init__(self, db: Database):
        self.db = db
    
    # =========================================================================
    # TRADE RETRIEVAL QUERIES
    # =========================================================================
    
    def get_best_performers(self, limit: int = 10) -> List[Dict]:
        """Get best performing trades."""
        
        trades = self.db.get_closed_trades(limit=100)
        sorted_trades = sorted(trades, key=lambda x: x.get("pnl_pct", 0), reverse=True)
        return sorted_trades[:limit]
    
    def get_worst_performers(self, limit: int = 10) -> List[Dict]:
        """Get worst performing trades."""
        
        trades = self.db.get_closed_trades(limit=100)
        sorted_trades = sorted(trades, key=lambda x: x.get("pnl_pct", 0))
        return sorted_trades[:limit]
    
    def get_longest_holds(self, limit: int = 10) -> List[Dict]:
        """Get longest held trades."""
        
        trades = self.db.get_closed_trades(limit=100)
        sorted_trades = sorted(trades, key=lambda x: x.get("hold_days", 0), reverse=True)
        return sorted_trades[:limit]
    
    def get_fastest_wins(self, limit: int = 10) -> List[Dict]:
        """Get fastest winning trades."""
        
        trades = self.db.get_closed_trades(limit=100)
        winning = [t for t in trades if t.get("profitable")]
        sorted_trades = sorted(winning, key=lambda x: x.get("hold_days", 0))
        return sorted_trades[:limit]
    
    # =========================================================================
    # ANALYSIS QUERIES
    # =========================================================================
    
    def get_exit_reason_breakdown(self) -> Dict[str, int]:
        """Get breakdown of exit reasons."""
        
        trades = self.db.get_closed_trades(limit=100)
        breakdown = {}
        
        for trade in trades:
            reason = trade.get("exit_reason", "unknown")
            breakdown[reason] = breakdown.get(reason, 0) + 1
        
        return breakdown
    
    def get_option_type_performance(self) -> Dict:
        """Get performance comparison: calls vs puts."""
        
        trades = self.db.get_closed_trades()
        
        calls = [t for t in trades if t.get("option_type") == "CALL"]
        puts = [t for t in trades if t.get("option_type") == "PUT"]
        
        return {
            "calls": self._calculate_stats(calls),
            "puts": self._calculate_stats(puts),
        }
    
    def get_dte_performance(self) -> Dict:
        """Get performance by DTE buckets."""
        
        trades = self.db.get_closed_trades()
        
        buckets = {
            "14-21_days": [],
            "22-35_days": [],
            "36-45_days": [],
            "45+_days": [],
        }
        
        for trade in trades:
            dte = trade.get("entry_dte", 0)
            
            if 14 <= dte <= 21:
                buckets["14-21_days"].append(trade)
            elif 22 <= dte <= 35:
                buckets["22-35_days"].append(trade)
            elif 36 <= dte <= 45:
                buckets["36-45_days"].append(trade)
            else:
                buckets["45+_days"].append(trade)
        
        return {k: self._calculate_stats(v) for k, v in buckets.items()}
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _calculate_stats(self, trades: List[Dict]) -> Dict:
        """Calculate statistics for a list of trades."""
        
        if not trades:
            return {
                "count": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
            }
        
        winning = [t for t in trades if t.get("profitable")]
        losing = [t for t in trades if not t.get("profitable")]
        total_pnl = sum([t.get("pnl_dollars", 0) for t in trades])
        
        return {
            "count": len(trades),
            "winning": len(winning),
            "losing": len(losing),
            "win_rate_pct": len(winning) / len(trades) * 100,
            "total_pnl_dollars": round(total_pnl, 2),
            "avg_pnl_per_trade": round(total_pnl / len(trades), 2),
            "avg_win_pct": round(
                sum([t.get("pnl_pct", 0) for t in winning]) / len(winning), 2
            ) if winning else 0,
            "avg_loss_pct": round(
                sum([t.get("pnl_pct", 0) for t in losing]) / len(losing), 2
            ) if losing else 0,
        }
            
