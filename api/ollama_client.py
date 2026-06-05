"""
api/ollama_client.py - Ollama LLM API wrapper
Used for research and commentary only, NOT for trading decisions
"""

import requests
import json
from typing import Dict, Optional
from config.logger import logger
from config.settings import APIConfig

class OllamaClient:
    """Ollama local LLM client."""
    
    def __init__(self):
        self.logger = logger
        self.config = APIConfig()
        self.base_url = self.config.OLLAMA_BASE_URL
        self.model = self.config.OLLAMA_MODEL
        self.timeout = self.config.OLLAMA_TIMEOUT
    
    # =========================================================================
    # LLM INFERENCE
    # =========================================================================
    
    def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Generate text from Ollama.
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Creativity (0-1)
            max_tokens: Max response length
        
        Returns:
            Generated text or None
        """
        
        try:
            # Build request
            messages = []
            
            if system:
                messages.append({"role": "system", "content": system})
            
            messages.append({"role": "user", "content": prompt})
            
            # Call Ollama
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("message"):
                return result["message"]["content"]
            
            return None
        
        except requests.exceptions.Timeout:
            self.logger.warning("Ollama request timed out")
            return None
        except Exception as e:
            self.logger.warning(f"Error calling Ollama: {e}")
            return None
    
    # =========================================================================
    # RESEARCH & ANALYSIS (Non-trading use)
    # =========================================================================
    
    def analyze_trade_setup(self, trade_context: Dict) -> str:
        """
        Generate research/commentary on a trade setup.
        COMMENTARY ONLY - NOT FOR TRADING DECISIONS.
        
        Args:
            trade_context: Trade information
        
        Returns:
            LLM commentary
        """
        
        prompt = f"""
        Provide brief research commentary (2-3 sentences) on this options trade setup:
        
        Ticker: {trade_context.get('ticker')}
        Type: {trade_context.get('option_type')}
        Strike: {trade_context.get('strike')}
        
        Technical: RSI {trade_context.get('rsi')}, above MA50
        Volatility: IV at {trade_context.get('iv_percentile')}th percentile
        
        Note: This is for research/commentary only, not a trading signal.
        """
        
        system = "You are a financial research analyst. Provide brief, factual commentary."
        
        return self.generate(prompt, system, temperature=0.5, max_tokens=150) or "No commentary available"
    
    def market_summary(self, market_data: Dict) -> str:
        """Generate market summary commentary."""
        
        prompt = f"""
        Provide a brief market overview (2-3 sentences) based on:
        
        VIX: {market_data.get('vix')}
        S&P 500 Change: {market_data.get('sp500_change')}%
        Most Active: {market_data.get('most_active')}
        
        This is for research context only.
        """
        
        system = "You are a market analyst. Provide brief, factual summary."
        
        return self.generate(prompt, system, temperature=0.5, max_tokens=100) or "No summary available"
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def is_available(self) -> bool:
        """Check if Ollama is running and available."""
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
