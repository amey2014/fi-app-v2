"""
main.py - Main application entry point
Orchestrates the trading bot with paper trading simulation
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import time
from typing import Optional
# Load environment
load_dotenv(override=True)
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from api.alpaca_client import AlpacaClient
from core.technical_analyzer import TechnicalAnalyzer
from core.decision_engine import DecisionEngine
from core.paper_trader import PaperTrader
from core.risk_manager import RiskManager
from storage.database import Database
class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self, use_paper_trading: bool = True):
        """
        Initialize trading bot.
        
        Args:
            use_paper_trading: If True, use PaperTrader (simulation)
                             If False, use real Alpaca API
        """
        self.use_paper_trading = use_paper_trading
        self.running = False
        
        # Initialize components
        logger.info("="*70)
        logger.info("INITIALIZING TRADING BOT")
        logger.info("="*70)
        
        try:
            # API Client
            self.alpaca = AlpacaClient()
            logger.info("[OK] Alpaca API connected")
            
            # Get account info
            account = self.alpaca.get_account()
            if 'error' not in account:
                logger.info(f"    Account: ${account['portfolio_value']:,.2f}")
                logger.info(f"    Cash: ${account['cash']:,.2f}")
                logger.info(f"    Buying Power: ${account['buying_power']:,.2f}")
            
            # Technical Analyzer
            self.analyzer = TechnicalAnalyzer()
            logger.info("[OK] Technical Analyzer initialized")
            
            # Risk Manager
            self.risk_manager = RiskManager()
            logger.info("[OK] Risk Manager initialized")
            
            # Trader (Paper or Real)
            if use_paper_trading:
                self.trader = PaperTrader(initial_capital=100000)
                logger.info("[OK] PaperTrader initialized (SIMULATION MODE)")
                logger.info("    Note: Trades are SIMULATED, not actual orders")
            else:
                # TODO: Implement RealTrader class
                self.trader = PaperTrader(initial_capital=100000)
                logger.warning("[WARN] RealTrader not implemented, using PaperTrader")
            
            # Decision Engine
            self.decision_engine = DecisionEngine(self.trader, self.risk_manager)
            logger.info("[OK] Decision Engine initialized")
            
            # Database
            self.db = Database()
            logger.info("[OK] Database connected")
            
            logger.info("="*70)
            logger.info("ALL SYSTEMS INITIALIZED SUCCESSFULLY")
            logger.info("="*70)
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def check_market_status(self) -> bool:
        """Check if market is open."""
        try:
            is_open = self.alpaca.is_market_open()
            status = "OPEN" if is_open else "CLOSED"
            logger.info(f"[MARKET] Status: {status}")
            return is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def scan_stock(self, symbol: str) -> Optional[dict]:
        """
        Scan a single stock for trading opportunities.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Trade signal or None
        """
        
        try:
            # Fetch price data (5-minute bars)
            logger.debug(f"Fetching bars for {symbol}...")
            bars = self.alpaca.get_bars(symbol, '5Min', limit=100)
            
            if not bars:
                logger.debug(f"{symbol}: No bars returned")
                return None
            
            if len(bars) < 50:
                logger.debug(f"{symbol}: Insufficient data ({len(bars)} bars, need 50)")
                return None
            
            logger.debug(f"{symbol}: Got {len(bars)} bars")
            
            # Convert to pandas Series
            closes = []
            highs = []
            lows = []
            volumes = []
            
            for bar in bars:
                try:
                    closes.append(float(bar.c))
                    highs.append(float(bar.h))
                    lows.append(float(bar.l))
                    volumes.append(int(bar.v))
                except Exception as e:
                    logger.warning(f"{symbol}: Error parsing bar: {e}")
                    continue
            
            if len(closes) < 50:
                logger.debug(f"{symbol}: Not enough valid bars ({len(closes)})")
                return None
            
            prices = pd.Series(closes)
            high = pd.Series(highs)
            low = pd.Series(lows)
            volume = pd.Series(volumes)
            
            # Get latest price
            current_price = prices.iloc[-1]
            
            logger.debug(f"{symbol}: Current price ${current_price:.2f}")
            
            # Technical analysis
            signal = self.analyzer.generate_trading_signal(prices, high, low, volume)
            
            logger.debug(f"{symbol}: Signal = {signal['signal']}, Confidence = {signal['confidence']:.1f}%")
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'signal': signal,
                'timestamp': datetime.now(),
            }
        
        except Exception as e:
            logger.debug(f"Error scanning {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_scan_result(self, scan_result: dict) -> bool:
        """
        Process scan result and potentially execute trade.
        
        Args:
            scan_result: Result from scan_stock()
        
        Returns:
            True if trade was executed
        """
        
        symbol = scan_result['symbol']
        current_price = scan_result['current_price']
        signal = scan_result['signal']
        
        # Evaluate if trade should be placed
        trade_params = self.decision_engine.evaluate_trade_signal(
            symbol, signal, current_price
        )
        
        if trade_params:
            # Execute trade
            return self.decision_engine.execute_trade(trade_params)
        
        return False
    
    def manage_positions(self):
        """Monitor and manage open positions."""
        
        for symbol in list(self.trader.open_positions.keys()):
            try:
                # Get current price
                bar = self.alpaca.get_latest_bar(symbol)
                if not bar:
                    logger.warning(f"Could not get latest bar for {symbol}")
                    continue
                
                current_price = float(bar.c)
                
                # Update position P&L
                self.trader.update_position(symbol, current_price)
                
                # Check exit conditions
                exit_reason = self.trader.check_exit_conditions(symbol, current_price)
                
                if exit_reason:
                    # Close position
                    self.trader.close_position(symbol, current_price, exit_reason)
                
                # Check time-based exit
                elif self.trader.check_time_exit(symbol, max_hold_minutes=120):
                    self.trader.close_position(symbol, current_price, "TIME_EXIT")
            
            except Exception as e:
                logger.error(f"Error managing position {symbol}: {e}")
    
    def print_status(self):
        """Print current account status."""
        account = self.trader.get_account_summary()
        
        print(f"\n[TIME] {datetime.now().strftime('%H:%M:%S')}")
        print(f"[BALANCE] Portfolio: ${account['portfolio_value']:,.2f} | "
              f"Cash: ${account['current_balance']:,.2f}")
        print(f"[P&L] Realized: ${account['total_realized_pnl']:+,.2f} | "
              f"Unrealized: ${account['total_unrealized_pnl']:+,.2f} | "
              f"Daily: ${account['daily_pnl']:+,.2f}")
        print(f"[TRADES] Open: {account['open_positions_count']} | "
              f"Total: {account['total_trades']} | "
              f"Win Rate: {account['win_rate']:.1f}%")
    
    def print_detailed_status(self):
        """Print detailed trading status."""
        print("\n" + "="*70)
        self.trader.print_account_summary()
        self.trader.print_open_positions()
        self.trader.print_closed_trades(limit=5)
    
    def run(self, watchlist: list, max_cycles: int = None, cycle_delay: int = 60):
        """
        Run main trading loop.
        
        Args:
            watchlist: List of symbols to scan
            max_cycles: Maximum cycles to run (None = infinite)
            cycle_delay: Delay between cycles in seconds
        """
        
        self.running = True
        cycle = 0
        
        logger.info(f"\n{'='*70}")
        logger.info("STARTING TRADING BOT")
        logger.info(f"Mode: {'PAPER TRADING (SIMULATION)' if self.use_paper_trading else 'LIVE TRADING'}")
        logger.info(f"Watchlist: {len(watchlist)} symbols")
        logger.info(f"Cycle Delay: {cycle_delay} seconds")
        logger.info(f"{'='*70}\n")
        
        try:
            while self.running:
                cycle += 1
                
                # Check if max cycles reached
                if max_cycles and cycle > max_cycles:
                    logger.info(f"Max cycles ({max_cycles}) reached. Stopping.")
                    break
                
                logger.info(f"\n{'='*70}")
                logger.info(f"SCAN CYCLE #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*70}")
                
                # Check market status
                if not self.check_market_status():
                    logger.info("Market closed. Waiting...")
                    time.sleep(cycle_delay)
                    continue
                
                # Scan all stocks
                trades_placed = 0
                scans_completed = 0
                scans_failed = 0
                
                logger.info(f"\nScanning {len(watchlist)} stocks...\n")
                
                for i, symbol in enumerate(watchlist, 1):
                    try:
                        # Scan stock
                        scan_result = self.scan_stock(symbol)
                        
                        if scan_result:
                            scans_completed += 1
                            
                            # Log signal
                            signal = scan_result['signal']
                            logger.info(
                                f"[{i:2d}] {symbol:5s}: {signal['signal']:6s} "
                                f"(Confidence: {signal['confidence']:6.1f}%) | "
                                f"Price: ${scan_result['current_price']:8.2f}"
                            )
                            
                            # Process signal
                            if self.process_scan_result(scan_result):
                                trades_placed += 1
                        else:
                            scans_failed += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        scans_failed += 1
                
                # Manage open positions
                if self.trader.open_positions:
                    logger.info(f"\nManaging {len(self.trader.open_positions)} open position(s)...")
                    self.manage_positions()
                
                # Print status
                self.print_status()
                
                # Log cycle summary
                logger.info(
                    f"\nCycle Summary: "
                    f"Scans Completed: {scans_completed}/{len(watchlist)} | "
                    f"Scans Failed: {scans_failed} | "
                    f"Trades Placed: {trades_placed}"
                )
                
                # Wait before next cycle
                logger.info(f"\nWaiting {cycle_delay} seconds until next cycle...")
                time.sleep(cycle_delay)
        
        except KeyboardInterrupt:
            logger.info("\nBot stopped by user (Ctrl+C)")
        
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the bot."""
        logger.info(f"\n{'='*70}")
        logger.info("SHUTTING DOWN TRADING BOT")
        logger.info(f"{'='*70}")
        
        self.running = False
        
        # Close any remaining positions
        if self.trader.open_positions:
            logger.warning(f"Closing {len(self.trader.open_positions)} open position(s)...")
            
            for symbol in list(self.trader.open_positions.keys()):
                try:
                    bar = self.alpaca.get_latest_bar(symbol)
                    if bar:
                        exit_price = float(bar.c)
                        self.trader.close_position(symbol, exit_price, "BOT_SHUTDOWN")
                except Exception as e:
                    logger.error(f"Error closing {symbol}: {e}")
        
        # Print final summary
        self.print_detailed_status()
        
        # Close database
        try:
            self.db.close()
            logger.info("[OK] Database closed")
        except:
            pass
        
        logger.info("Bot shutdown complete")
def get_watchlist() -> list:
    """Get default watchlist of stocks to scan."""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
        'TSLA', 'META', 'NFLX', 'INTC', 'AMD',
        'ADBE', 'CRM', 'CSCO', 'IBM', 'QCOM',
        'AVGO', 'PYPL', 'INTU', 'ASML', 'BKNG',
        'ABNB', 'DASH', 'UBER', 'LCID', 'NIO',
        'RIVN', 'PLTR', 'SQ', 'ZM', 'SNOW',
        'DDOG', 'CRWD', 'NET', 'PSTG', 'OKTA',
        'ACN', 'TXN', 'BROADCOM', 'XLNX', 'MU',
        'STX', 'WDC', 'MCHP', 'KEYS', 'MPWR',
        'TPH', 'HPQ', 'JNPR', 'DELL', 'CDW',
    ]
def main():
    """Main entry point."""
    
    print("\n" + "="*70)
    print("TRADING BOT - PAPER TRADING MODE")
    print("="*70)
    print("\nConfiguration:")
    print("  Mode: Paper Trading (SIMULATION)")
    print("  Actual Alpaca orders will NOT be placed")
    print("  All trades are simulated for testing logic")
    print("  Database will track all simulated trades")
    print("\n" + "="*70)
    
    # Initialize bot with PAPER TRADING
    bot = TradingBot(use_paper_trading=True)
    
    # Get watchlist
    watchlist = get_watchlist()
    
    # Run bot
    # Cycle delay: 60 seconds for testing (use 300 for 5 minutes in production)
    # max_cycles: 10 for testing, None for infinite
    try:
        bot.run(
            watchlist=watchlist,
            max_cycles=10,        # Run 10 cycles for testing
            cycle_delay=60        # 60 seconds between cycles
        )
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    main()
