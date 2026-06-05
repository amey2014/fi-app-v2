"""
core/risk_calculator.py - Position sizing and risk management
Calculates position size, stop loss, and profit targets
"""

import numpy as np
from datetime import datetime
from typing import Dict, Optional
from scipy.stats import norm
from config.logger import logger
from config.settings import TradingConfig

class RiskCalculator:
    """Calculate position sizing and risk management."""
    
    def __init__(self):
        self.logger = logger
        self.config = TradingConfig()
    
    # =========================================================================
    # POSITION SIZING
    # =========================================================================
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        portfolio_value: float,
        capital_limit: float = None,
        max_loss_pct: float = 0.02
    ) -> Dict:
        """
        Calculate optimal position size based on risk management.
        
        Args:
            entry_price: Entry price per contract (in dollars)
            stop_loss_price: Stop loss price
            portfolio_value: Total portfolio value
            capital_limit: Max capital per trade (overrides %)
            max_loss_pct: Max % of portfolio to risk per trade (default 2%)
        
        Returns:
            Dict with position sizing details
        """
        
        try:
            # Risk per contract
            risk_per_contract = entry_price - stop_loss_price
            
            if risk_per_contract <= 0:
                return {
                    "error": "Stop loss must be below entry price",
                    "contracts": 0,
                }
            
            # Max dollar loss per trade
            max_dollar_loss = portfolio_value * max_loss_pct
            
            # Calculate contracts (1 contract = 100 shares for options)
            contracts = max_dollar_loss / risk_per_contract / 100
            contracts = int(contracts)
            
            # Apply capital limit if provided
            if capital_limit:
                max_contracts_by_capital = int(capital_limit / (entry_price * 100))
                contracts = min(contracts, max_contracts_by_capital)
            
            # Apply config limit
            max_contracts_config = int(self.config.CAPITAL_PER_TRADE / (entry_price * 100))
            contracts = min(contracts, max_contracts_config)
            
            # Minimum 1 contract
            contracts = max(1, contracts)
            
            # Calculate actual position cost
            position_cost = contracts * entry_price * 100
            actual_max_loss = contracts * risk_per_contract * 100
            actual_risk_pct = actual_max_loss / portfolio_value * 100
            
            return {
                "contracts": contracts,
                "position_cost": position_cost,
                "max_loss_dollars": actual_max_loss,
                "max_loss_pct": actual_risk_pct,
                "risk_per_contract": risk_per_contract,
                "feasible": contracts > 0,
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return {"error": str(e), "contracts": 0}
    
    # =========================================================================
    # PROFIT TARGETS & STOP LOSS
    # =========================================================================
    
    def calculate_targets(
        self,
        entry_price: float,
        strike: float,
        stock_price: float,
        dte: int,
        iv_percentile: float,
        probability_of_profit: float,
        option_type: str = "CALL"
    ) -> Dict:
        """
        Calculate profit targets and stop loss based on probabilities.
        
        Args:
            entry_price: Entry premium paid
            strike: Strike price
            stock_price: Current stock price
            dte: Days to expiration
            iv_percentile: IV percentile (0-100)
            probability_of_profit: PoP calculated by Greeks
            option_type: "CALL" or "PUT"
        
        Returns:
            Dict with target levels
        """
        
        try:
            # Dynamic targets based on probability
            if probability_of_profit > 0.70:
                # High probability (70%+ PoP)
                tp1_multiplier = 1.25
                tp2_multiplier = 1.50
                stop_loss_multiplier = 0.70
            elif probability_of_profit > 0.60:
                # Medium probability (60-70%)
                tp1_multiplier = 1.40
                tp2_multiplier = 1.80
                stop_loss_multiplier = 0.65
            else:
                # Lower probability (<60%)
                tp1_multiplier = 1.60
                tp2_multiplier = 2.20
                stop_loss_multiplier = 0.50
            
            # Calculate target prices
            take_profit_1 = entry_price * tp1_multiplier
            take_profit_2 = entry_price * tp2_multiplier
            stop_loss = entry_price * stop_loss_multiplier
            
            # Profit percentages
            tp1_pct = (tp1_multiplier - 1) * 100
            tp2_pct = (tp2_multiplier - 1) * 100
            stop_pct = (stop_loss_multiplier - 1) * 100
            
            # Validate risk-reward ratio
            risk = entry_price - stop_loss
            reward_1 = take_profit_1 - entry_price
            reward_2 = take_profit_2 - entry_price
            
            rr_ratio_1 = reward_1 / risk if risk > 0 else 0
            rr_ratio_2 = reward_2 / risk if risk > 0 else 0
            
            # Check if meets minimum R:R requirement
            min_ratio = self.config.MIN_RISK_REWARD_RATIO
            meets_requirement = rr_ratio_1 >= min_ratio
            
            return {
                "entry_price": entry_price,
                "take_profit_1": round(take_profit_1, 2),
                "take_profit_1_pct": round(tp1_pct, 1),
                "take_profit_2": round(take_profit_2, 2),
                "take_profit_2_pct": round(tp2_pct, 1),
                "stop_loss": round(stop_loss, 2),
                "stop_loss_pct": round(stop_pct, 1),
                "risk_reward_ratio_1": round(rr_ratio_1, 2),
                "risk_reward_ratio_2": round(rr_ratio_2, 2),
                "meets_minimum_rr": meets_requirement,
                "probability_of_profit_pct": round(probability_of_profit * 100, 1),
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating targets: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # PROBABILITY CALCULATIONS
    # =========================================================================
    
    def calculate_expected_value(
        self,
        win_probability: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        win_count: int = 0,
        loss_count: int = 0
    ) -> Dict:
        """
        Calculate expected value of a trade.
        
        Args:
            win_probability: Probability of win (0-1)
            avg_win_pct: Average win percentage
            avg_loss_pct: Average loss percentage (negative)
            win_count: Historical wins (for context)
            loss_count: Historical losses (for context)
        
        Returns:
            Dict with EV calculations
        """
        
        try:
            loss_probability = 1 - win_probability
            
            # Expected value = (P_win × Avg_win) - (P_loss × Avg_loss)
            expected_value = (win_probability * avg_win_pct) - (loss_probability * abs(avg_loss_pct))
            
            # Calculate win rate needed for positive EV
            # 0 = (P_win × Avg_win) - ((1 - P_win) × Avg_loss)
            # P_win_breakeven = Avg_loss / (Avg_win + Avg_loss)
            if (avg_win_pct + abs(avg_loss_pct)) > 0:
                win_rate_needed = abs(avg_loss_pct) / (avg_win_pct + abs(avg_loss_pct))
            else:
                win_rate_needed = 0.5
            
            return {
                "expected_value_pct": round(expected_value, 2),
                "positive_ev": expected_value > 0,
                "win_rate_breakeven": round(win_rate_needed * 100, 1),
                "current_win_rate": round(win_probability * 100, 1) if win_count + loss_count > 0 else None,
                "historical_trades": win_count + loss_count,
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating EV: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # KELLY CRITERION (Position Sizing Optimization)
    # =========================================================================
    
    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> Dict:
        """
        Calculate Kelly Criterion for optimal position sizing.
        
        Kelly % = (bp - q) / b
        where:
        - b = odds (avg_win / avg_loss)
        - p = win probability
        - q = loss probability (1 - p)
        
        Note: Use 1/4 Kelly (fractional Kelly) for safety
        
        Args:
            win_rate: Win rate as decimal (0-1)
            avg_win: Average win in %
            avg_loss: Average loss in % (negative)
        
        Returns:
            Dict with Kelly calculations
        """
        
        try:
            if win_rate <= 0 or win_rate >= 1:
                return {"error": "Invalid win rate"}
            
            p = win_rate
            q = 1 - win_rate
            b = avg_win / abs(avg_loss) if avg_loss != 0 else 1
            
            # Kelly Criterion
            kelly_pct = (b * p - q) / b
            
            # Use fractional Kelly for safety (1/4 Kelly)
            fractional_kelly = kelly_pct / 4
            
            return {
                "kelly_criterion_pct": round(kelly_pct * 100, 1),
                "fractional_kelly_1_4": round(fractional_kelly * 100, 1),
                "recommended_position_size": round(max(0, fractional_kelly) * 100, 1),
                "note": "Fractional Kelly recommended for risk management",
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating Kelly: {e}")
            return {"error": str(e)}
