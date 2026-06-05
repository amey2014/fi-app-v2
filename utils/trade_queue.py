"""
utils/trade_queue.py - Inter-process communication for trading commands
Allows dashboard to send commands to main trading bot
"""

import queue
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TradeCommand:
    """Command from dashboard to bot."""
    
    command_type: str  # "EXIT", "CANCEL", "PAUSE", "RESUME"
    symbol: Optional[str] = None
    portion: Optional[float] = None  # 0.0-1.0 (e.g., 0.5 for half)
    order_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TradeCommandQueue:
    """Thread-safe queue for bot commands."""
    
    def __init__(self, maxsize: int = 100):
        self.queue = queue.Queue(maxsize=maxsize)
    
    def put_command(self, command: TradeCommand) -> bool:
        """
        Add command to queue.
        
        Args:
            command: TradeCommand object
        
        Returns:
            True if successful
        """
        
        try:
            self.queue.put(command, block=False)
            return True
        except queue.Full:
            return False
    
    def get_command(self, timeout: float = 0.1) -> Optional[TradeCommand]:
        """
        Get next command from queue.
        
        Args:
            timeout: Wait time in seconds
        
        Returns:
            TradeCommand or None
        """
        
        try:
            return self.queue.get(block=True, timeout=timeout)
        except queue.Empty:
            return None
    
    def has_commands(self) -> bool:
        """Check if queue has pending commands."""
        return not self.queue.empty()
    
    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()


# Global queue instance
command_queue = TradeCommandQueue()


def add_exit_command(symbol: str, portion: float = 1.0) -> bool:
    """Helper: Add exit command."""
    
    command = TradeCommand(
        command_type="EXIT",
        symbol=symbol,
        portion=portion
    )
    return command_queue.put_command(command)


def add_cancel_command(order_id: str) -> bool:
    """Helper: Add cancel command."""
    
    command = TradeCommand(
        command_type="CANCEL",
        order_id=order_id
    )
    return command_queue.put_command(command)
