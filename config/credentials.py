"""
config/credentials.py - Credentials management
"""
import os
from typing import Optional
from config.logger import logger
class CredentialsManager:
    """Manage API credentials securely."""
    
    @staticmethod
    def get_alpaca_credentials() -> dict:
        """Get Alpaca API credentials."""
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not secret_key:
            logger.error("Missing Alpaca credentials in .env file")
            raise ValueError("APCA_API_KEY_ID and APCA_API_SECRET_KEY required")
        
        return {
            "api_key": api_key,
            "secret_key": secret_key,
            "base_url": base_url,
            "is_paper_trading": "paper" in base_url.lower(),
        }
    
    @staticmethod
    def validate_credentials() -> bool:
        """Validate all required credentials are available."""
        try:
            CredentialsManager.get_alpaca_credentials()
            logger.info("[Ok] Credentials validated")
            return True
        except ValueError as e:
            logger.error(f"✗ Credential validation failed: {e}")
            return False