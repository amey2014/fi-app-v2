"""
monitoring/exit_manager.py - Exit execution and trade closure
Executes exits and logs closed trades
"""

from datetime import datetime
from typing import Dict, List, Optional
from config.logger import logger
from config.settings import TradingConfig

class ExitManager:
    """Manage trade exits and closures."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
    
    # =========================================================================
    # EXIT EXECUTION
    # =========================================================================
    
    def build_exit_order(
        self,
        position: Dict,
        exit_signal: Dict,
        current_price: float
    ) -> Dict:
        """
        Build exit order from exit signal.
        
        Args:
            position: Original position dict
            exit_signal: Exit condition signal
            current_price: Current option price
        
        Returns:
            Dict with exit order details
        """
        
        try:
            symbol = position.get("symbol", "")
            
            # Determine exit quantity
            if exit_signal.get("exit_type") == "PARTIAL":
                qty = exit_signal.get("exit_quantity", 1)
            else:
                qty = position.get("qty", 1)
            
            exit_order = {
                "symbol": symbol,
                "side": "sell",
                "qty": qty,
                "order_type": "market",
                "time_in_force": "day",
                "exit_reason": exit_signal.get("exit_reason"),
                "exit_trigger": exit_signal.get("trigger"),
                "exit_price": current_price,
                "estimated_proceeds": current_price * qty * 100,
                "timestamp": datetime.now().isoformat(),
            }
            
            return exit_order
        
        except Exception as e:
            self.logger.error(f"Error building exit order: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # TRADE CLOSURE LOGGING
    # =========================================================================
    
    def create_closed_trade_record(
        self,
        entry_data: Dict,
        exit_data: Dict,
        position_analysis: Dict
    ) -> Dict:
        """
        Create a complete closed trade record.
        
        Args:
            entry_data: Original entry data
            exit_data: Exit execution data
            position_analysis: Final position analysis
        
        Returns:
            Dict with complete trade record
        """
        
        try:
            entry_price = entry_data.get("entry_price", 0)
            exit_price = exit_data.get("exit_price", 0)
            entry_qty = entry_data.get("contracts", 1)
            exit_qty = exit_data.get("qty", entry_qty)
            
            # Calculate P&L
            # For options: P&L = (exit_price - entry_price) * contracts * 100
            pl_dollars = (exit_price - entry_price) * exit_qty * 100
            pl_pct = (exit_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
            
            # Get hold time
            entry_time = datetime.fromisoformat(entry_data.get("entry_time", datetime.now().isoformat()))
            exit_time = datetime.fromisoformat(exit_data.get("timestamp", datetime.now().isoformat()))
            hold_time = exit_time - entry_time
            hold_days = hold_time.days
            hold_hours = hold_time.total_seconds() / 3600
            
            closed_trade = {
                "trade_id": entry_data.get("trade_id"),
                "ticker": entry_data.get("ticker"),
                "option_type": entry_data.get("option_type"),
                "strike": entry_data.get("strike"),
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "hold_days": hold_days,
                "hold_hours": round(hold_hours, 2),
                
                # Entry details
                "entry_price": entry_price,
                "entry_qty": entry_qty,
                "entry_cost": entry_price * entry_qty * 100,
                "entry_dte": entry_data.get("entry_dte"),
                
                # Exit details
                "exit_price": exit_price,
                "exit_qty": exit_qty,
                "exit_proceeds": exit_price * exit_qty * 100,
                "exit_reason": exit_data.get("exit_reason"),
                "exit_trigger": exit_data.get("exit_trigger"),
                
                # P&L
                "pnl_dollars": round(pl_dollars, 2),
                "pnl_pct": round(pl_pct, 2),
                "profitable": pl_dollars > 0,
                
                # Market context
                "entry_iv": entry_data.get("entry_iv"),
                "exit_iv": position_analysis.get("exit_iv"),
                "entry_rsi": entry_data.get("entry_rsi"),
                "entry_vix": entry_data.get("entry_vix"),
                
                # Status
                "status": "CLOSED",
                "created_at": datetime.now().isoformat(),
            }
            
            return closed_trade
        
        except Exception as e:
            self.logger.error(f"Error creating closed trade record: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # RECOVERY TRADE LOGIC
    # =========================================================================
    
    def should_attempt_recovery(
        self,
        closed_trade: Dict,
        recent_trades: List[Dict]
    ) -> Dict:
        """
        Determine if a recovery trade should be attempted after a loss.
        
        Args:
            closed_trade: Just-closed losing trade
            recent_trades: Recent trades for context
        
        Returns:
            Dict with recovery decision
        """
        
        try:
            # Only attempt recovery on losses
            if closed_trade.get("profitable", False):
                return {
                    "should_recover": False,
                    "reason": "Trade was profitable, no recovery needed",
                }
            
            pl_pct = closed_trade.get("pnl_pct", 0)
            
            # Check consecutive losses
            recent_losses = [t for t in recent_trades[-5:] if not t.get("profitable", False)]
            
            if len(recent_losses) >= self.config.MAX_CONSECUTIVE_LOSSES:
                return {
                    "should_recover": False,
                    "reason": f"Hit max consecutive losses ({self.config.MAX_CONSECUTIVE_LOSSES})",
                }
            
            # Check if loss is severe enough to warrant recovery
            if pl_pct > -15:  # Small losses don't need recovery
                return {
                    "should_recover": False,
                    "reason": "Loss too small to warrant recovery trade",
                }
            
            # Determine opposite direction
            original_type = closed_trade.get("option_type")
            recovery_type = "PUT" if original_type == "CALL" else "CALL"
            
            return {
                "should_recover": True,
                "recovery_type": recovery_type,
                "original_type": original_type,
                "loss_amount": abs(closed_trade.get("pnl_dollars", 0)),
                "reason": f"Attempt recovery with opposite {recovery_type}",
            }
        
        except Exception as e:
            self.logger.error(f"Error determining recovery: {e}")
            return {"should_recover": False, "reason": f"Error: {e}"}
    
    # =========================================================================
    # EXIT SUMMARY GENERATION
    # =========================================================================
    
    def generate_exit_summary(self, closed_trades: List[Dict]) -> Dict:
        """
        Generate summary of exit performance.
        
        Args:
            closed_trades: List of closed trade records
        
        Returns:
            Dict with exit summary
        """
        
        if not closed_trades:
            return {"error": "No closed trades"}
        
        try:
            profitable = [t for t in closed_trades if t.get("profitable")]
            losing = [t for t in closed_trades if not t.get("profitable")]
            
            total_pl = sum([t.get("pnl_dollars", 0) for t in closed_trades])
            avg_pl = total_pl / len(closed_trades) if closed_trades else 0
            
            exit_reasons = {}
            for trade in closed_trades:
                reason = trade.get("exit_reason", "unknown")
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
            
            return {
                "total_closed_trades": len(closed_trades),
                "profitable_trades": len(profitable),
                "losing_trades": len(losing),
                "win_rate_pct": len(profitable) / len(closed_trades) * 100,
                "total_pnl": round(total_pl, 2),
                "average_pnl_per_trade": round(avg_pl, 2),
                "avg_win": round(
                    sum([t.get("pnl_pct", 0) for t in profitable]) / len(profitable), 2
                ) if profitable else 0,
                "avg_loss": round(
                    sum([t.get("pnl_pct", 0) for t in losing]) / len(losing), 2
                ) if losing else 0,
                "exit_reasons": exit_reasons,
            }
        
        except Exception as e:
            self.logger.error(f"Error generating exit summary: {e}")
            return {"error": str(e)}
