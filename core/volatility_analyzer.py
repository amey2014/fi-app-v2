"""
core/volatility_analyzer.py - Volatility and Greeks analysis
Analyzes IV, calculates Greeks, and generates volatility signals
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from scipy.stats import norm
from config.logger import logger
from config.settings import TradingConfig
class VolatilityAnalyzer:
    """Analyze implied volatility and option Greeks."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
    
    # =========================================================================
    # BLACK-SCHOLES GREEKS CALCULATION
    # =========================================================================
    
    def calculate_greeks(
        self,
        option_type: str,
        spot: float,
        strike: float,
        dte: int,
        iv: float,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0
    ) -> Dict:
        """
        Calculate option Greeks using Black-Scholes model.
        
        Args:
            option_type: "CALL" or "PUT"
            spot: Current stock price
            strike: Strike price
            dte: Days to expiration
            iv: Implied Volatility (as decimal, e.g., 0.25 for 25%)
            risk_free_rate: Risk-free rate (default 5%)
            dividend_yield: Dividend yield (default 0%)
        
        Returns:
            Dict with Greeks (delta, gamma, theta, vega, rho)
        """
        
        try:
            # Convert DTE to years
            T = dte / 365.0
            
            # Validate inputs
            if T <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
                return self._get_null_greeks()
            
            r = risk_free_rate
            q = dividend_yield
            S = spot
            K = strike
            sigma = iv
            
            # Calculate d1 and d2
            d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Cumulative normal distributions
            N_d1 = norm.cdf(d1)
            N_d2 = norm.cdf(d2)
            n_d1 = norm.pdf(d1)
            
            if option_type.upper() == "CALL":
                # Call Greeks
                delta = np.exp(-q * T) * N_d1
                gamma = np.exp(-q * T) * n_d1 / (S * sigma * np.sqrt(T))
                theta = (
                    -S * np.exp(-q * T) * n_d1 * sigma / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * N_d2
                    + q * S * np.exp(-q * T) * N_d1
                ) / 365  # Annualized to daily
                vega = S * np.exp(-q * T) * n_d1 * np.sqrt(T) / 100  # Per 1% IV change
                rho = K * T * np.exp(-r * T) * N_d2 / 100  # Per 1% rate change
                
            else:  # PUT
                N_d1_neg = norm.cdf(-d1)
                N_d2_neg = norm.cdf(-d2)
                
                delta = -np.exp(-q * T) * N_d1_neg
                gamma = np.exp(-q * T) * n_d1 / (S * sigma * np.sqrt(T))
                theta = (
                    S * np.exp(-q * T) * n_d1 * sigma / (2 * np.sqrt(T))
                    + r * K * np.exp(-r * T) * N_d2_neg
                    - q * S * np.exp(-q * T) * N_d1_neg
                ) / 365  # Daily theta
                vega = S * np.exp(-q * T) * n_d1 * np.sqrt(T) / 100  # Per 1% IV change
                rho = -K * T * np.exp(-r * T) * N_d2_neg / 100
            
            return {
                "delta": float(delta),
                "gamma": float(gamma),
                "theta": float(theta),
                "vega": float(vega),
                "rho": float(rho),
                "success": True,
            }
        
        except Exception as e:
            self.logger.warning(f"Error calculating Greeks: {e}")
            return self._get_null_greeks()
    
    def _get_null_greeks(self) -> Dict:
        """Return null Greeks dict."""
        return {
            "delta": None,
            "gamma": None,
            "theta": None,
            "vega": None,
            "rho": None,
            "success": False,
        }
    
    # =========================================================================
    # IV PERCENTILE & ANALYSIS
    # =========================================================================
    
    def calculate_iv_metrics(
        self,
        current_iv: float,
        iv_history: List[float],
        ticker: str = None
    ) -> Dict:
        """
        Calculate IV percentile and trend metrics.
        
        Args:
            current_iv: Current IV value
            iv_history: List of historical IV values (252 days minimum)
            ticker: Ticker symbol for logging
        
        Returns:
            Dict with IV metrics
        """
        
        if not iv_history or len(iv_history) < 20:
            return {
                "iv_percentile": None,
                "iv_rank": None,
                "iv_trend": "UNKNOWN",
                "iv_assessment": "INSUFFICIENT_DATA",
            }
        
        # Convert to numpy array for calculations
        iv_array = np.array(iv_history)
        
        # Calculate percentiles
        iv_52w_high = np.max(iv_array)
        iv_52w_low = np.min(iv_array)
        iv_20d_avg = np.mean(iv_array[-20:])
        iv_50d_avg = np.mean(iv_array[-50:]) if len(iv_array) >= 50 else np.mean(iv_array)
        
        # IV Percentile (0-100)
        if iv_52w_high > iv_52w_low:
            iv_percentile = ((current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low)) * 100
        else:
            iv_percentile = 50.0
        
        iv_percentile = max(0, min(100, iv_percentile))  # Clamp 0-100
        
        # IV Rank (similar to percentile but uses rank)
        sorted_iv = np.sort(iv_array)
        rank_position = np.searchsorted(sorted_iv, current_iv)
        iv_rank = (rank_position / len(sorted_iv)) * 100 if len(sorted_iv) > 0 else 50
        
        # Trend analysis
        if current_iv > iv_20d_avg * 1.15:
            iv_trend = "ELEVATED"
        elif current_iv < iv_20d_avg * 0.85:
            iv_trend = "COMPRESSED"
        else:
            iv_trend = "NORMAL"
        
        # Assessment for trading
        if iv_percentile > 75:
            assessment = "VERY_EXPENSIVE"
            trading_signal = "SKIP_OR_SELL"
        elif iv_percentile > 60:
            assessment = "EXPENSIVE"
            trading_signal = "CAUTIOUS"
        elif iv_percentile < 25:
            assessment = "VERY_CHEAP"
            trading_signal = "IDEAL_BUY"
        elif iv_percentile < 40:
            assessment = "CHEAP"
            trading_signal = "GOOD_BUY"
        else:
            assessment = "NORMAL"
            trading_signal = "STANDARD"
        
        return {
            "current_iv": float(current_iv),
            "iv_percentile": float(iv_percentile),
            "iv_rank": float(iv_rank),
            "iv_52w_high": float(iv_52w_high),
            "iv_52w_low": float(iv_52w_low),
            "iv_20d_avg": float(iv_20d_avg),
            "iv_50d_avg": float(iv_50d_avg),
            "iv_trend": iv_trend,
            "assessment": assessment,
            "trading_signal": trading_signal,
        }
    
    # =========================================================================
    # OPTIONS CHAIN ENRICHMENT WITH GREEKS
    # =========================================================================
    
    def enrich_options_chain(
        self,
        calls_df: pd.DataFrame,
        puts_df: pd.DataFrame,
        stock_price: float,
        iv_percentile: float,
        ticker: str = None
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Enrich options chain data with calculated Greeks.
        
        Args:
            calls_df: DataFrame with call options
            puts_df: DataFrame with put options
            stock_price: Current stock price
            iv_percentile: IV percentile for context
            ticker: Ticker symbol for logging
        
        Returns:
            Tuple of (enriched_calls, enriched_puts)
        """
        
        enriched_calls = []
        enriched_puts = []
        
        # Process calls
        if not calls_df.empty:
            for _, row in calls_df.iterrows():
                try:
                    enriched_call = self._enrich_single_option(
                        row=row,
                        option_type="CALL",
                        stock_price=stock_price,
                        iv_percentile=iv_percentile
                    )
                    if enriched_call:
                        enriched_calls.append(enriched_call)
                except Exception as e:
                    self.logger.debug(f"Error enriching call: {e}")
                    continue
        
        # Process puts
        if not puts_df.empty:
            for _, row in puts_df.iterrows():
                try:
                    enriched_put = self._enrich_single_option(
                        row=row,
                        option_type="PUT",
                        stock_price=stock_price,
                        iv_percentile=iv_percentile
                    )
                    if enriched_put:
                        enriched_puts.append(enriched_put)
                except Exception as e:
                    self.logger.debug(f"Error enriching put: {e}")
                    continue
        
        return enriched_calls, enriched_puts
    
    def _enrich_single_option(self, row: pd.Series, option_type: str, stock_price: float, iv_percentile: float) -> Optional[Dict]:
        """Enrich a single option contract with Greeks."""
        
        try:
            strike = float(row.get("strike", 0))
            dte = int(row.get("dte", 0))
            bid = float(row.get("bid", 0))
            ask = float(row.get("ask", 0))
            volume = int(row.get("volume", 0))
            open_interest = int(row.get("openInterest", 0))
            iv = float(row.get("impliedVolatility", 0.2))  # Default 20% if missing
            
            # Skip invalid data
            if strike <= 0 or dte <= 0 or ask <= 0:
                return None
            
            # Calculate Greeks
            greeks = self.calculate_greeks(
                option_type=option_type,
                spot=stock_price,
                strike=strike,
                dte=dte,
                iv=iv
            )
            
            if not greeks.get("success"):
                return None
            
            # Calculate metrics
            mid_price = (bid + ask) / 2 if bid > 0 else ask
            spread_pct = ((ask - bid) / mid_price * 100) if mid_price > 0 else 0
            moneyness = strike / stock_price if stock_price > 0 else 1.0
            
            # Determine quality score
            quality_score = self._calculate_option_quality(
                bid=bid,
                ask=ask,
                volume=volume,
                open_interest=open_interest,
                spread_pct=spread_pct,
                delta=greeks["delta"],
                theta=greeks["theta"],
                vega=greeks["vega"],
                iv_percentile=iv_percentile
            )
            
            return {
                "strike": float(strike),
                "dte": dte,
                "bid": float(bid),
                "ask": float(ask),
                "mid": float(mid_price),
                "spread_pct": float(spread_pct),
                "volume": volume,
                "open_interest": open_interest,
                "iv": float(iv),
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "rho": greeks["rho"],
                "moneyness": float(moneyness),
                "quality_score": quality_score,
                "expiry": str(row.get("expiry", "")),
            }
        
        except Exception as e:
            self.logger.debug(f"Error enriching option: {e}")
            return None
    
    def _calculate_option_quality(
        self,
        bid: float,
        ask: float,
        volume: int,
        open_interest: int,
        spread_pct: float,
        delta: float,
        theta: float,
        vega: float,
        iv_percentile: float
    ) -> float:
        """
        Calculate overall quality score for an option (0-100).
        
        Factors:
        - Liquidity (bid/ask spread)
        - Volume & OI
        - Greeks profile
        - IV context
        """
        
        score = 50  # Start with neutral
        
        # Liquidity score (30 points)
        if spread_pct < 2:
            score += 10
        elif spread_pct < 5:
            score += 5
        
        # Volume score (20 points)
        if volume > 100:
            score += 10
        elif volume > 50:
            score += 5
        
        # OI score (20 points)
        if open_interest > 1000:
            score += 10
        elif open_interest > 500:
            score += 5
        
        # Greeks profile score (20 points)
        # Good theta decay (positive for short, negative for long calls)
        if theta > 0.01:  # Daily theta decay
            score += 5
        
        # Reasonable vega exposure
        if 0 < vega < 0.05:
            score += 5
        
        # IV context (10 points)
        if 40 < iv_percentile < 70:  # Normal IV
            score += 5
        
        return max(0, min(100, score))
    
    # =========================================================================
    # IV SKEW ANALYSIS
    # =========================================================================
    
    def analyze_iv_skew(self, calls_df: List[Dict], puts_df: List[Dict]) -> Dict:
        """
        Analyze IV skew between calls and puts.
        
        Args:
            calls_df: List of enriched call options
            puts_df: List of enriched put options
        
        Returns:
            Dict with skew metrics
        """
        
        if not calls_df or not puts_df:
            return {"skew": None, "interpretation": "INSUFFICIENT_DATA"}
        
        # Get ATM (At-The-Money) IV for comparison
        calls_iv = [c["iv"] for c in calls_df if c.get("iv")]
        puts_iv = [p["iv"] for p in puts_df if p.get("iv")]
        
        if not calls_iv or not puts_iv:
            return {"skew": None, "interpretation": "INSUFFICIENT_DATA"}
        
        avg_call_iv = np.mean(calls_iv)
        avg_put_iv = np.mean(puts_iv)
        
        # IV Skew ratio
        skew_ratio = avg_put_iv / avg_call_iv if avg_call_iv > 0 else 1.0
        skew_pct = (skew_ratio - 1) * 100
        
        # Interpretation
        if skew_pct > 10:
            interpretation = "PUTS_EXPENSIVE"  # Fear premium in puts
            signal = "SKEWED_TO_DOWNSIDE"
        elif skew_pct < -10:
            interpretation = "CALLS_EXPENSIVE"  # Bullish skew
            signal = "SKEWED_TO_UPSIDE"
        else:
            interpretation = "BALANCED"
            signal = "NEUTRAL_SKEW"
        
        return {
            "skew_pct": float(skew_pct),
            "skew_ratio": float(skew_ratio),
            "avg_call_iv": float(avg_call_iv),
            "avg_put_iv": float(avg_put_iv),
            "interpretation": interpretation,
            "signal": signal,
        }
    
    # =========================================================================
    # PROBABILITY CALCULATIONS
    # =========================================================================
    
    def calculate_probability_of_profit(
        self,
        spot: float,
        strike: float,
        dte: int,
        iv: float,
        option_type: str
    ) -> float:
        """
        Calculate probability that option will be profitable at expiration.
        
        Args:
            spot: Current stock price
            strike: Strike price
            dte: Days to expiration
            iv: Implied volatility
            option_type: "CALL" or "PUT"
        
        Returns:
            Probability (0.0 to 1.0)
        """
        
        try:
            T = dte / 365.0
            
            if T <= 0 or iv <= 0:
                return 0.5  # 50% baseline
            
            d2 = (np.log(spot / strike) + (0.05 - 0.5 * iv ** 2) * T) / (iv * np.sqrt(T))
            
            if option_type.upper() == "CALL":
                prob = norm.cdf(d2)
            else:  # PUT
                prob = norm.cdf(-d2)
            
            return float(prob)
        
        except Exception as e:
            self.logger.debug(f"Error calculating PoP: {e}")
            return 0.5
    
    # =========================================================================
    # VOLATILITY CONE
    # =========================================================================
    
    def calculate_volatility_cone(self, historical_volatility: List[float]) -> Dict:
        """
        Calculate volatility cone (percentiles of historical volatility).
        
        Args:
            historical_volatility: List of daily volatility values
        
        Returns:
            Dict with volatility percentiles
        """
        
        if not historical_volatility or len(historical_volatility) < 20:
            return {"error": "Insufficient data"}
        
        vol_array = np.array(historical_volatility)
        
        return {
            "vol_10th": float(np.percentile(vol_array, 10)),
            "vol_25th": float(np.percentile(vol_array, 25)),
            "vol_50th": float(np.percentile(vol_array, 50)),
            "vol_75th": float(np.percentile(vol_array, 75)),
            "vol_90th": float(np.percentile(vol_array, 90)),
            "vol_current": float(vol_array[-1]),
        }
