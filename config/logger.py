"""
config/logger.py - Centralized logging setup
"""
import logging
import logging.handlers
import os
from config.settings import LogConfig
def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Setup a logger with both file and console handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional custom log file path
    
    Returns:
        Configured logger instance
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LogConfig.LOG_LEVEL))
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LogConfig.LOG_FILE), exist_ok=True)
    
    # Format
    formatter = logging.Formatter(LogConfig.LOG_FORMAT)
    
    # File handler with rotation
    if not log_file:
        log_file = LogConfig.LOG_FILE
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=LogConfig.LOG_MAX_BYTES,
        backupCount=LogConfig.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    if not logger.handlers:  # Avoid duplicate handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
# Root logger
logger = setup_logger("trading_bot")
