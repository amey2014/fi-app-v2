"""
core/options_selector.py - Smart options contract selection
Selects the best contract based on multiple criteria
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from config.logger import logger
from config.settings import TradingConfig

class OptionsSelector:
    """Select optimal option contracts for trading."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
    
    # =========================================================================
    # MAIN SELECTION LOGIC
    # =========================================================================
    
    def select_best_option(
        self,
        ticker: str,
        option_type: str,  # "CALL" or "PUT"
        options_list: List[Dict],
        stock_price: float,
        iv_percentile: float,
        portfolio_size: float = 50000
    ) -> Optional[Dict]:
        """
        Select the single best option contract.
        
        Args:
            ticker: Stock ticker
            option_type: "CALL" or "PUT"
            options_list: List of option dicts with Greeks
            stock_price: Current stock price
            iv_percentile: IV percentile (0-100)
            portfolio_size: Total portfolio size
        
        Returns:
            Best option dict or None
        """
        
        # Step 1: Filter by DTE
        dte_filtered = self._filter_by_dte(options_list)
        if not dte_filtered:
            self.logger.warning(f"No options in optimal DTE range for {ticker}")
            return None
        
        # Step 2: Filter by liquidity
        liquidity_filtered = self._filter_by_liquidity(dte_filtered)
        if not liquidity_filtered:
            self.logger.warning(f"No liquid options for {ticker}")
            return None
        
        # Step 3: Determine optimal delta range based on IV
        delta_range = self._get_delta_range_for_iv(iv_percentile)
        
        # Step 4: Filter by delta
        delta_filtered = self._filter_by_delta(liquidity_filtered, delta_range)
        if not delta_filtered:
            self.logger.warning(f"No options with optimal delta for {ticker}")
            # Fallback to closest delta
            delta_filtered = liquidity_filtered
        
        # Step 5: Filter by theta
        theta_filtered = self._filter_by_theta(delta_filtered)
        if not theta_filtered:
            theta_filtered = delta_filtered  # Fallback if no good theta
        
        # Step 6: Filter by vega
        vega_filtered = self._filter_by_vega(theta_filtered, portfolio_size)
        if not vega_filtered:
            vega_filtered = theta_filtered  # Fallback
        
        # Step 7: Score and rank
        scored_options = self._score_options(vega_filtered, stock_price, iv_percentile)
        
        if not scored_options:
            return None
        
        # Return top option
        best_option = scored_options[0]
        
        self.logger.info(
            f"Selected {option_type} {ticker} Strike=${best_option['strike']} "
            f"Delta={best_option['delta']:.2f} Theta={best_option['theta']:.4f} "
            f"Score={best_option['selection_score']:.1f}"
        )
        
        return best_option
    
    def select_multiple_options(
        self,
        ticker: str,
        option_type: str,
        options_list: List[Dict],
        stock_price: float,
        iv_percentile: float,
        portfolio_size: float = 50000,
        count: int = 3
    ) -> List[Dict]:
        """
        Select multiple option contracts (alternatives).
        
        Args:
            ticker: Stock ticker
            option_type: "CALL" or "PUT"
            options_list: List of option dicts
            stock_price: Current stock price
            iv_percentile: IV percentile
            portfolio_size: Total portfolio size
            count: Number of options to return
        
        Returns:
            List of option dicts (top N)
        """
        
        # Apply all filters
        dte_filtered = self._filter_by_dte(options_list)
        if not dte_filtered:
            return []
        
        liquidity_filtered = self._filter_by_liquidity(dte_filtered)
        if not liquidity_filtered:
            return []
        
        delta_range = self._get_delta_range_for_iv(iv_percentile)
        delta_filtered = self._filter_by_delta(liquidity_filtered, delta_range)
        if not delta_filtered:
            delta_filtered = liquidity_filtered
        
        theta_filtered = self._filter_by_theta(delta_filtered)
        if not theta_filtered:
            theta_filtered = delta_filtered
        
        vega_filtered = self._filter_by_vega(theta_filtered, portfolio_size)
        if not vega_filtered:
            vega_filtered = theta_filtered
        
        # Score and sort
        scored_options = self._score_options(vega_filtered, stock_price, iv_percentile)
        
        return scored_options[:count]
    
    # =========================================================================
    # FILTER METHODS
    # =========================================================================
    
    def _filter_by_dte(self, options_list: List[Dict]) -> List[Dict]:
        """Filter by DTE range."""
        
        min_dte, max_dte = self.config.OPTIMAL_DTE_RANGE
        
        filtered = [
            opt for opt in options_list
            if min_dte <= opt.get("dte", 0) <= max_dte
        ]
        
        if not filtered:
            # Fallback to broader range
            filtered = [
                opt for opt in options_list
                if self.config.MIN_DTE <= opt.get("dte", 0) <= self.config.MAX_DTE
            ]
        
        return filtered
    
    def _filter_by_liquidity(self, options_list: List[Dict]) -> List[Dict]:
        """Filter by bid/ask spread and volume."""
        
        filtered = [
            opt for opt in options_list
            if (opt.get("volume", 0) >= self.config.MIN_LIQUIDITY_VOLUME and
                opt.get("open_interest", 0) >= self.config.MIN_LIQUIDITY_OI and
                opt.get("spread_pct", 100) < 10)  # Less than 10% spread
        ]
        
        return filtered
    
    def _filter_by_delta(self, options_list: List[Dict], delta_range: Tuple[float, float]) -> List[Dict]:
        """Filter by delta range."""
        
        min_delta, max_delta = delta_range
        
        filtered = [
            opt for opt in options_list
            if min_delta <= abs(opt.get("delta", 0)) <= max_delta
        ]
        
        return filtered
    
    def _filter_by_theta(self, options_list: List[Dict], min_theta: float = 0.005) -> List[Dict]:
        """Filter by positive theta (time decay in our favor)."""
        
        filtered = [
            opt for opt in options_list
            if opt.get("theta", 0) >= min_theta
        ]
        
        return filtered
    
    def _filter_by_vega(self, options_list: List[Dict], portfolio_size: float) -> List[Dict]:
        """Filter by vega exposure."""
        
        max_vega = portfolio_size * 0.1  # Max 10% of portfolio exposed to IV
        
        filtered = [
            opt for opt in options_list
            if opt.get("vega", 0) <= max_vega
        ]
        
        return filtered
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_delta_range_for_iv(self, iv_percentile: float) -> Tuple[float, float]:
        """
        Get delta range based on IV percentile.
        
        High IV → Sell more OTM (lower delta)
        Low IV → Sell closer to ATM (higher delta)
        """
        
        if iv_percentile > 60:
            return self.config.DELTA_RANGE_HIGH_IV
        elif iv_percentile < 40:
            return self.config.DELTA_RANGE_LOW_IV
        else:
            return self.config.DELTA_RANGE_NORMAL_IV
    
    def _score_options(self, options_list: List[Dict], stock_price: float, iv_percentile: float) -> List[Dict]:
        """
        Score options on multiple criteria and sort.
        
        Scoring factors:
        - Theta decay (40%)
        - Delta proximity to target (30%)
        - Bid/ask spread (20%)
        - Gamma exposure (10%)
        """
        
        scored = []
        
        for opt in options_list:
            try:
                score = 0
                
                # Theta score (40 points max)
                theta = opt.get("theta", 0)
                max_theta = 0.05
                theta_score = min(40, (theta / max_theta) * 40) if max_theta > 0 else 0
                
                # Delta score (30 points max) - target 0.45 delta
                delta = abs(opt.get("delta", 0))
                target_delta = 0.45
                delta_distance = abs(delta - target_delta)
                delta_score = max(0, 30 - (delta_distance * 30))
                
                # Spread score (20 points max)
                spread_pct = opt.get("spread_pct", 10)
                spread_score = max(0, 20 - (spread_pct * 2))
                
                # Gamma score (10 points max) - lower is better
                gamma = opt.get("gamma", 0)
                max_gamma = 0.01
                gamma_score = max(0, 10 - (gamma / max_gamma * 10))
                
                # Total score
                total_score = theta_score + delta_score + spread_score + gamma_score
                
                opt_copy = opt.copy()
                opt_copy["selection_score"] = total_score
                scored.append(opt_copy)
            
            except Exception as e:
                self.logger.debug(f"Error scoring option: {e}")
                continue
        
        # Sort by score descending
        scored.sort(key=lambda x: x["selection_score"], reverse=True)
        
        return scored
