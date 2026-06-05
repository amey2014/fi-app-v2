"""
core/technical_analyzer.py - Technical analysis engine
Calculates indicators and generates signals
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
from config.logger import logger
from config.settings import TechnicalThresholds

class TechnicalAnalyzer:
    """Calculate technical indicators and generate trading signals."""
    
    def __init__(self):
        """Initialize analyzer with thresholds from settings."""
        self.logger = logger
        
        # Import thresholds from settings
        try:
            from config.settings import TechnicalThresholds
            
            self.rsi_overbought = TechnicalThresholds.RSI_OVERBOUGHT.value
            self.rsi_oversold = TechnicalThresholds.RSI_OVERSOLD.value
            self.rsi_very_overbought = TechnicalThresholds.RSI_VERY_OVERBOUGHT.value
            self.rsi_very_oversold = TechnicalThresholds.RSI_VERY_OVERSOLD.value
            self.macd_threshold = TechnicalThresholds.MACD_DIVERGENCE_THRESHOLD.value
            self.stoch_rsi_threshold = TechnicalThresholds.STOCH_RSI_THRESHOLD.value
            self.bb_stddev = TechnicalThresholds.BB_STDDEV.value
            self.volume_multiplier = TechnicalThresholds.MIN_DAILY_VOLUME_MULTIPLIER.value
            
            self.logger.info("[OK] Technical thresholds loaded from settings")
            
        except ImportError as e:
            # Fallback defaults if settings not found
            self.logger.warning(f"Could not import thresholds from settings: {e}")
            self.logger.warning("Using default threshold values")
            
            self.rsi_overbought = 70
            self.rsi_oversold = 30
            self.rsi_very_overbought = 80
            self.rsi_very_oversold = 20
            self.macd_threshold = 0.001
            self.stoch_rsi_threshold = 0.20
            self.bb_stddev = 2.0
            self.volume_multiplier = 0.5
        
        except AttributeError as e:
            self.logger.error(f"Error accessing threshold values: {e}")
            raise
    
    # =========================================================================
    # RSI - RELATIVE STRENGTH INDEX
    # =========================================================================
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        
        Args:
            prices: Series of prices
            period: Period for calculation (default 14)
        
        Returns:
            Series with RSI values
        """
        
        if len(prices) < period + 1:
            return pd.Series([np.nan] * len(prices))
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_rsi_signal(self, rsi: float) -> str:
        """
        Get RSI signal interpretation.
        
        Args:
            rsi: RSI value
        
        Returns:
            Signal string
        """
        
        if rsi >= self.rsi_very_overbought:
            return "VERY_OVERBOUGHT"
        elif rsi >= self.rsi_overbought:
            return "OVERBOUGHT"
        elif rsi <= self.rsi_very_oversold:
            return "VERY_OVERSOLD"
        elif rsi <= self.rsi_oversold:
            return "OVERSOLD"
        else:
            return "NEUTRAL"
    
    # =========================================================================
    # MACD - MOVING AVERAGE CONVERGENCE DIVERGENCE
    # =========================================================================
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Series of prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
        
        Returns:
            Dict with MACD, signal, and histogram
        """
        
        if len(prices) < slow + signal:
            return {
                "macd": None,
                "signal": None,
                "histogram": None,
                "trend": "UNKNOWN",
            }
        
        # Calculate EMAs
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        # Calculate MACD
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        # Get current values
        current_macd = macd.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        # Determine trend
        if current_histogram > self.macd_threshold and current_macd > current_signal:
            trend = "BULLISH"
        elif current_histogram < -self.macd_threshold and current_macd < current_signal:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            "macd": float(current_macd),
            "signal": float(current_signal),
            "histogram": float(current_histogram),
            "trend": trend,
            "series_macd": macd,
            "series_signal": signal_line,
            "series_histogram": histogram,
        }
    
    # =========================================================================
    # STOCHASTIC RSI
    # =========================================================================
    
    def calculate_stochastic_rsi(self, prices: pd.Series, period: int = 14, k: int = 3, d: int = 3) -> Dict:
        """
        Calculate Stochastic RSI (faster momentum indicator).
        
        Args:
            prices: Series of prices
            period: RSI period
            k: K smoothing period
            d: D smoothing period
        
        Returns:
            Dict with Stochastic RSI values
        """
        
        if len(prices) < period + k + d:
            return {"k": None, "d": None, "signal": "UNKNOWN"}
        
        # Calculate RSI first
        rsi = self.calculate_rsi(prices, period)
        
        # Calculate Stochastic RSI
        lowest_rsi = rsi.rolling(window=period).min()
        highest_rsi = rsi.rolling(window=period).max()
        
        stoch_rsi = (rsi - lowest_rsi) / (highest_rsi - lowest_rsi)
        
        # K and D lines
        k_line = stoch_rsi.rolling(window=k).mean()
        d_line = k_line.rolling(window=d).mean()
        
        current_k = k_line.iloc[-1]
        current_d = d_line.iloc[-1]
        
        # Signal based on stochastic threshold
        if current_k > (1 - self.stoch_rsi_threshold):
            signal = "OVERBOUGHT"
        elif current_k < self.stoch_rsi_threshold:
            signal = "OVERSOLD"
        else:
            signal = "NEUTRAL"
        
        return {
            "k": float(current_k) if pd.notna(current_k) else None,
            "d": float(current_d) if pd.notna(current_d) else None,
            "signal": signal,
        }
    
    # =========================================================================
    # BOLLINGER BANDS
    # =========================================================================
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = None) -> Dict:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: Series of prices
            period: Period for moving average
            std_dev: Standard deviations for bands (uses settings if None)
        
        Returns:
            Dict with band values
        """
        
        if std_dev is None:
            std_dev = self.bb_stddev
        
        if len(prices) < period:
            return {
                "upper": None,
                "middle": None,
                "lower": None,
                "width_pct": None,
                "signal": "UNKNOWN",
            }
        
        # Calculate middle band (SMA)
        middle = prices.rolling(window=period).mean()
        
        # Calculate standard deviation
        std = prices.rolling(window=period).std()
        
        # Calculate bands
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        current_price = prices.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]
        
        # Calculate band width
        band_width = current_upper - current_lower
        band_width_pct = (band_width / current_middle * 100) if current_middle != 0 else 0
        
        # Determine if price is near bands
        if current_price >= current_upper * 0.95:
            signal = "NEAR_UPPER"
        elif current_price <= current_lower * 1.05:
            signal = "NEAR_LOWER"
        else:
            signal = "INSIDE_BANDS"
        
        return {
            "upper": float(current_upper) if pd.notna(current_upper) else None,
            "middle": float(current_middle) if pd.notna(current_middle) else None,
            "lower": float(current_lower) if pd.notna(current_lower) else None,
            "width_pct": float(band_width_pct),
            "signal": signal,
        }
    
    # =========================================================================
    # ATR - AVERAGE TRUE RANGE
    # =========================================================================
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Measures volatility.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of close prices
            period: Period for calculation
        
        Returns:
            Series with ATR values
        """
        
        if len(high) < period:
            return pd.Series([np.nan] * len(high))
        
        # Calculate True Range
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    # =========================================================================
    # VOLUME ANALYSIS
    # =========================================================================
    
    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV).
        
        Measures buying/selling pressure.
        
        Args:
            close: Series of close prices
            volume: Series of volumes
        
        Returns:
            Series with OBV values
        """
        
        if len(close) < 2:
            return pd.Series([np.nan] * len(close))
        
        obv = pd.Series([0.0] * len(close))
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def calculate_volume_trend(self, close: pd.Series, volume: pd.Series, period: int = 20) -> str:
        """
        Determine volume trend (increasing/decreasing).
        
        Args:
            close: Series of close prices
            volume: Series of volumes
            period: Period for comparison
        
        Returns:
            Trend direction
        """
        
        if len(volume) < period:
            return "UNKNOWN"
        
        recent_avg_volume = volume.tail(period).mean()
        prior_avg_volume = volume.tail(period * 2).head(period).mean()
        
        threshold = self.volume_multiplier
        
        if recent_avg_volume > prior_avg_volume * (1 + threshold):
            return "INCREASING"
        elif recent_avg_volume < prior_avg_volume * (1 - threshold):
            return "DECREASING"
        else:
            return "STABLE"
    
    # =========================================================================
    # SUPPORT & RESISTANCE
    # =========================================================================
    
    def find_support_resistance(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> Dict:
        """
        Find key support and resistance levels.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of close prices
            period: Period for finding levels
        
        Returns:
            Dict with key levels
        """
        
        if len(high) < period:
            return {
                "resistance_1": None,
                "support_1": None,
                "pivot": None,
            }
        
        # Get recent highs and lows
        recent_high = high.tail(period).max()
        recent_low = low.tail(period).min()
        recent_close = close.iloc[-1]
        
        # Pivot point
        pivot = (recent_high + recent_low + recent_close) / 3
        
        # Support and Resistance (based on recent ranges)
        resistance_1 = recent_high
        resistance_2 = pivot + (recent_high - recent_low)
        support_1 = recent_low
        support_2 = pivot - (recent_high - recent_low)
        
        current_price = close.iloc[-1]
        
        # Distance to levels
        distance_to_resistance = (resistance_1 - current_price) / current_price * 100
        distance_to_support = (current_price - support_1) / current_price * 100
        
        return {
            "resistance_1": float(resistance_1),
            "resistance_2": float(resistance_2),
            "pivot": float(pivot),
            "support_1": float(support_1),
            "support_2": float(support_2),
            "current_price": float(current_price),
            "distance_to_resistance": float(distance_to_resistance),
            "distance_to_support": float(distance_to_support),
        }
    
    # =========================================================================
    # MOMENTUM INDICATORS
    # =========================================================================
    
    def calculate_momentum(self, prices: pd.Series, period: int = 10) -> pd.Series:
        """
        Calculate Price Momentum.
        
        Args:
            prices: Series of prices
            period: Period for calculation
        
        Returns:
            Series with momentum values
        """
        
        if len(prices) < period:
            return pd.Series([np.nan] * len(prices))
        
        momentum = prices.diff(period)
        return momentum
    
    def calculate_roc(self, prices: pd.Series, period: int = 12) -> pd.Series:
        """
        Calculate Rate of Change (ROC).
        
        Args:
            prices: Series of prices
            period: Period for calculation
        
        Returns:
            Series with ROC values
        """
        
        if len(prices) < period:
            return pd.Series([np.nan] * len(prices))
        
        roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
        return roc
    
    # =========================================================================
    # MOVING AVERAGES
    # =========================================================================
    
    def calculate_moving_averages(self, prices: pd.Series) -> Dict:
        """
        Calculate multiple moving averages.
        
        Args:
            prices: Series of prices
        
        Returns:
            Dict with various MAs
        """
        
        result = {}
        
        # Simple Moving Averages
        for period in [5, 10, 20, 50, 200]:
            if len(prices) >= period:
                result[f'sma_{period}'] = float(prices.rolling(window=period).mean().iloc[-1])
            else:
                result[f'sma_{period}'] = None
        
        # Exponential Moving Averages
        for period in [12, 26]:
            if len(prices) >= period:
                result[f'ema_{period}'] = float(prices.ewm(span=period).mean().iloc[-1])
            else:
                result[f'ema_{period}'] = None
        
        return result
    
    def calculate_ma_crossover(self, prices: pd.Series, fast: int = 50, slow: int = 200) -> str:
        """
        Determine MA crossover signal.
        
        Args:
            prices: Series of prices
            fast: Fast MA period
            slow: Slow MA period
        
        Returns:
            Signal string
        """
        
        if len(prices) < slow:
            return "UNKNOWN"
        
        fast_ma = prices.rolling(window=fast).mean()
        slow_ma = prices.rolling(window=slow).mean()
        
        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        
        if current_fast > current_slow:
            return "BULLISH"
        elif current_fast < current_slow:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    # =========================================================================
    # COMBINED SIGNAL GENERATION
    # =========================================================================
    
    def generate_trading_signal(self, prices: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Dict:
        """
        Generate comprehensive trading signal from all indicators.
        
        Args:
            prices: Series of close prices
            high: Series of high prices
            low: Series of low prices
            volume: Series of volumes
        
        Returns:
            Dict with signal and confidence score
        """
        
        signal_scores = {}
        confidence = 0
        signals = []
        
        # RSI Signal
        rsi_series = self.calculate_rsi(prices)
        if pd.notna(rsi_series.iloc[-1]):
            rsi = rsi_series.iloc[-1]
            rsi_signal = self.get_rsi_signal(rsi)
            
            if rsi_signal == "OVERSOLD":
                signal_scores['rsi'] = 50
                signals.append("RSI_OVERSOLD")
            elif rsi_signal == "VERY_OVERSOLD":
                signal_scores['rsi'] = 75
                signals.append("RSI_VERY_OVERSOLD")
            elif rsi_signal == "OVERBOUGHT":
                signal_scores['rsi'] = -50
                signals.append("RSI_OVERBOUGHT")
            elif rsi_signal == "VERY_OVERBOUGHT":
                signal_scores['rsi'] = -75
                signals.append("RSI_VERY_OVERBOUGHT")
            else:
                signal_scores['rsi'] = 0
        
        # MACD Signal
        macd_data = self.calculate_macd(prices)
        if macd_data['trend'] == "BULLISH":
            signal_scores['macd'] = 40
            signals.append("MACD_BULLISH")
        elif macd_data['trend'] == "BEARISH":
            signal_scores['macd'] = -40
            signals.append("MACD_BEARISH")
        else:
            signal_scores['macd'] = 0
        
        # Bollinger Bands Signal
        bb_data = self.calculate_bollinger_bands(prices)
        if bb_data['signal'] == "NEAR_LOWER":
            signal_scores['bb'] = 30
            signals.append("BB_NEAR_LOWER")
        elif bb_data['signal'] == "NEAR_UPPER":
            signal_scores['bb'] = -30
            signals.append("BB_NEAR_UPPER")
        else:
            signal_scores['bb'] = 0
        
        # Volume Signal
        volume_trend = self.calculate_volume_trend(prices, volume)
        if volume_trend == "INCREASING":
            signal_scores['volume'] = 25
            signals.append("VOLUME_INCREASING")
        else:
            signal_scores['volume'] = 0
        
        # MA Crossover Signal
        ma_signal = self.calculate_ma_crossover(prices)
        if ma_signal == "BULLISH":
            signal_scores['ma'] = 30
            signals.append("MA_BULLISH")
        elif ma_signal == "BEARISH":
            signal_scores['ma'] = -30
            signals.append("MA_BEARISH")
        else:
            signal_scores['ma'] = 0
        
        # Calculate overall confidence
        confidence = sum(signal_scores.values()) / len(signal_scores) if signal_scores else 0
        confidence = max(-100, min(100, confidence))  # Clamp to -100 to 100
        
        # Determine overall signal direction
        if confidence > 40:
            overall_signal = "BUY"
        elif confidence < -40:
            overall_signal = "SELL"
        else:
            overall_signal = "NEUTRAL"
        
        return {
            "signal": overall_signal,
            "confidence": float(confidence),
            "component_scores": signal_scores,
            "signals": signals,
            "rsi": float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else None,
            "macd_trend": macd_data['trend'],
        }

