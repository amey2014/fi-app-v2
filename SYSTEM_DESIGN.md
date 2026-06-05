# Trading Bot System Design & Architecture

## TABLE OF CONTENTS
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Data Flow](#data-flow)
4. [Core Components](#core-components)
5. [Technical Analysis Engine](#technical-analysis-engine)
6. [Decision Engine](#decision-engine)
7. [Trade Execution](#trade-execution)
8. [Risk Management](#risk-management)
9. [Monitoring & Logging](#monitoring--logging)
10. [Workflow Examples](#workflow-examples)

---

## SYSTEM OVERVIEW

### Purpose
Automated options trading bot that:
- Scans multiple stocks for trading opportunities
- Analyzes technical indicators to generate BUY/SELL signals
- Manages multiple concurrent trades with strict risk controls
- Logs all trades and performance metrics
- Provides real-time monitoring dashboard

### Key Features
- **Multi-instrument scanning**: Monitors ~50 stocks simultaneously
- **Technical analysis**: RSI, MACD, Bollinger Bands, Volume, Support/Resistance
- **Smart trade management**: Position sizing, stop-loss, take-profit
- **Risk controls**: Daily loss limits, max concurrent trades, pattern day trader rules
- **Real-time dashboard**: Flask-based UI with live updates
- **Comprehensive logging**: Trade history, performance analytics, error tracking

---

## ARCHITECTURE DIAGRAM

================================================================================
                        TRADING BOT SYSTEM ARCHITECTURE
================================================================================

┌────────────────────────────────────────────────────────────────────────────┐
│                         TRADING BOT APPLICATION                            │
│                                                                            │
│  Automated Options Trading with Technical Analysis & Risk Management      │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│   API LAYER      │        │  CORE LOGIC      │        │   MONITORING     │
│  (Data Source)   │        │  (Decision Maker)│        │   (Tracking)     │
└──────────────────┘        └──────────────────┘        └──────────────────┘
        │                             │                             │
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ ALPACA API CLIENT    │  │ DECISION ENGINE      │  │ TRADE LOGGER         │
│ alpaca_client.py     │  │ decision_engine.py   │  │ trade_logger.py      │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • get_account()      │  │ • evaluate_signal()  │  │ • log_trade()        │
│ • get_bars()         │  │ • calculate_risk()   │  │ • log_indicator()    │
│ • get_clock()        │  │ • approve_trade()    │  │ • generate_report()  │
│ • submit_order()     │  │ • set_parameters()   │  │ • update_dashboard() │
│ • get_positions()    │  │                      │  │                      │
│ • close_position()   │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
        │                             │                             │
        │        ┌────────────────────┼────────────────────┐       │
        │        │                    │                    │       │
        ▼        ▼                    ▼                    ▼       ▼
    ┌────────────────────────────────────────────────────────────────────┐
    │                    TECHNICAL ANALYZER                              │
    │                  technical_analyzer.py                            │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  MOMENTUM INDICATORS          VOLATILITY          VOLUME           │
    │  ├─ RSI (14)                  ├─ ATR (14)         ├─ OBV           │
    │  ├─ MACD (12,26,9)            ├─ Bollinger Bands  ├─ Volume Trend  │
    │  ├─ Stochastic RSI            │   (20, 2σ)        │                │
    │  └─ Rate of Change            │                   │                │
    │                               │                   │                │
    │  PRICE ACTION                 SUPPORT/RESIST      SIGNAL GEN       │
    │  ├─ Moving Averages           ├─ Pivot Points    ├─ Score each    │
    │  │  (SMA, EMA)                ├─ Support Levels  │   indicator     │
    │  ├─ MA Crossover              ├─ Resist Levels   ├─ Calc confidence│
    │  └─ Momentum                  │                   └─ Return signal  │
    │                               │                                    │
    └────────────────────────────────────────────────────────────────────┘
        │                             │                             │
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ RISK MANAGER         │  │ TRADE MANAGER        │  │ DATABASE LAYER       │
│ risk_manager.py      │  │ trade_manager.py     │  │ database.py          │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • position_size()    │  │ • open_position()    │  │ • log_trade()        │
│ • calculate_risk()   │  │ • monitor_position() │  │ • update_trade()     │
│ • daily_limits()     │  │ • check_exit()       │  │ • query_trades()     │
│ • stop_loss()        │  │ • close_position()   │  │ • calc_performance() │
│ • take_profit()      │  │ • handle_errors()    │  │ • get_summary()      │
│ • compliance()       │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
        │                             │                             │
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ DATA STORAGE         │  │ CONFIGURATION        │  │ EXTERNAL SYSTEMS     │
│                      │  │ & SETTINGS           │  │                      │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ SQLite/PostgreSQL    │  │ .env (Credentials)   │  │ • Alpaca API         │
│ ├─ trades table      │  │ settings.py          │  │ • Market Data        │
│ ├─ indicators table  │  │ ├─ Thresholds       │  │ • News Feed (opt)    │
│ ├─ account_history   │  │ ├─ Risk Limits      │  │ • Email Alerts (opt) │
│ └─ daily_summary     │  │ └─ Trade Params     │  │                      │
│                      │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
        │                             │                             │
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ LOGGING & ALERTS     │  │ DASHBOARD (WEB UI)   │  │ MAIN APPLICATION     │
│                      │  │ ui/dashboard.py      │  │ main.py              │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • Console Logger     │  │ • Flask Server       │  │ • Initialize systems │
│ • File Logger        │  │ • Real-time Charts   │  │ • Main scan loop     │
│ • Error Tracking     │  │ • Account Metrics    │  │ • Error handling     │
│ • Email Alerts       │  │ • Trade History      │  │ • Graceful shutdown  │
│ • Slack (optional)   │  │ • Performance Stats  │  │                      │
│                      │  │ • Live Updates       │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘


================================================================================
                              DATA FLOW DIAGRAM
================================================================================

START APPLICATION
       │
       ├─→ [INITIALIZATION]
       │   ├─ Load .env credentials
       │   ├─ Connect to Alpaca API
       │   ├─ Connect to Database
       │   ├─ Initialize components
       │   └─ Start Flask dashboard
       │
       └─→ [MAIN LOOP] (Every 1-5 minutes)
           │
           ├─→ [1] CHECK MARKET STATUS
           │   └─ Is market open?
           │
           ├─→ [2] GET ACCOUNT INFO
           │   ├─ Current balance
           │   ├─ Available capital
           │   ├─ Open positions
           │   └─ Daily P&L
           │
           ├─→ [3] SCAN WATCHLIST (50 stocks)
           │   │
           │   └─→ FOR EACH STOCK:
           │       │
           │       ├─→ [A] FETCH PRICE DATA
           │       │   ├─ Get last 100 bars
           │       │   ├─ Calculate OHLCV
           │       │   └─ Store in memory
           │       │
           │       ├─→ [B] TECHNICAL ANALYSIS
           │       │   ├─ Calculate 10+ indicators
           │       │   ├─ Generate signal
           │       │   └─ Assign confidence score
           │       │
           │       ├─→ [C] RISK ASSESSMENT
           │       │   ├─ Calculate position size
           │       │   ├─ Set stop-loss/take-profit
           │       │   ├─ Check daily limits
           │       │   └─ Verify capital available
           │       │
           │       ├─→ [D] DECISION MAKING
           │       │   ├─ Is signal strong enough?
           │       │   ├─ All risk checks passed?
           │       │   └─ Place trade? YES/NO
           │       │
           │       └─→ [E] IF TRADE SIGNAL:
           │           ├─ Submit order to Alpaca
           │           ├─ Log to database
           │           ├─ Set alerts
           │           └─ Add to tracking
           │
           ├─→ [4] MANAGE OPEN POSITIONS
           │   │
           │   └─→ FOR EACH OPEN POSITION:
           │       ├─ Check current P&L
           │       ├─ Check stop-loss
           │       ├─ Check take-profit
           │       ├─ Check time limit
           │       └─ Close if condition met
           │
           ├─→ [5] LOG & UPDATE
           │   ├─ Update database
           │   ├─ Update dashboard
           │   ├─ Send alerts
           │   └─ Log metrics
           │
           └─→ [6] WAIT 1-5 MINUTES
               └─ Repeat loop


================================================================================
                      TRADE EXECUTION WORKFLOW
================================================================================

PHASE 1: SIGNAL GENERATION
┌─────────────────────────────────────┐
│ Technical Analysis                  │
├─────────────────────────────────────┤
│ Input: 100 price bars               │
│                                     │
│ Calculate:                          │
│ • RSI = 35 (OVERSOLD)              │
│ • MACD = BULLISH                   │
│ • BB = NEAR_LOWER                  │
│ • Volume = INCREASING              │
│ • MA = BULLISH_CROSS               │
│                                     │
│ Signal Score:                       │
│ (+50 +40 +30 +25 +30) / 5 = +35%   │
│                                     │
│ Output: BUY signal, 35% confidence  │
└─────────────────────────────────────┘
                │
                ▼
PHASE 2: RISK ASSESSMENT
┌─────────────────────────────────────┐
│ Risk Manager                        │
├─────────────────────────────────────┤
│ Inputs:                             │
│ • Entry price: $155                 │
│ • ATR: $2.15                        │
│ • Account: $80,500                  │
│ • Daily loss so far: -$200          │
│                                     │
│ Calculate:                          │
│ • Stop-loss: 155 - 2×2.15 = $150.70│
│ • Take-profit: 155 + 3×2.15 = $161.45│
│ • Max risk per trade: 1% = $805     │
│ • Position size: 5 shares           │
│ • Trade risk: 5 × $4.30 = $21.50   │
│                                     │
│ Checks:                             │
│ ✓ Risk < 1% of capital              │
│ ✓ Daily loss limit not hit          │
│ ✓ Open positions (2) < max (5)      │
│ ✓ Capital available                 │
└─────────────────────────────────────┘
                │
                ▼
PHASE 3: DECISION ENGINE
┌─────────────────────────────────────┐
│ Decision Making                     │
├─────────────────────────────────────┤
│ Final Checks:                       │
│ ✓ Signal confidence: 35% (OK)       │
│ ✓ Multiple confirming indicators    │
│ ✓ Stock volume adequate             │
│ ✓ No recent duplicate trade         │
│ ✓ Pattern day trader compliant      │
│                                     │
│ DECISION: APPROVE TRADE             │
│ Trade Parameters:                   │
│ • Symbol: AAPL                      │
│ • Side: BUY                         │
│ • Qty: 5 shares                     │
│ • Price: $155                       │
│ • Stop Loss: $150.70                │
│ • Take Profit: $161.45              │
└─────────────────────────────────────┘
                │
                ▼
PHASE 4: TRADE EXECUTION
┌─────────────────────────────────────┐
│ Trade Manager                       │
├─────────────────────────────────────┤
│ 1. Submit order to Alpaca           │
│    → Order ID: 12345                │
│    → Status: FILLED @ $155.02       │
│                                     │
│ 2. Log trade to database            │
│    → Entry timestamp                │
│    → Technical signal               │
│    → Position parameters            │
│                                     │
│ 3. Set monitoring                   │
│    → Track position price           │
│    → Monitor stop-loss              │
│    → Monitor take-profit            │
│    → Monitor time limit (2 hours)   │
│                                     │
│ Position Opened:                    │
│ AAPL: 5 shares @ $155.02            │
└─────────────────────────────────────┘
                │
                ▼
PHASE 5: POSITION MONITORING
┌─────────────────────────────────────┐
│ Continuous Monitoring               │
├─────────────────────────────────────┤
│ Every 30 seconds:                   │
│                                     │
│ Current: $156.50 (+$7.40)           │
│ P&L: +0.95%                         │
│                                     │
│ Checks:                             │
│ • Price > Stop Loss ($150.70)? YES  │
│ • Price > Take Profit ($161.45)?NO  │
│ • Technical deterioration? NO       │
│ • Time limit exceeded? NO           │
│                                     │
│ Action: HOLD POSITION               │
│                                     │
│ --- After 1 hour 45 mins ---        │
│                                     │
│ Current: $161.20 (+$31)             │
│ P&L: +4.01%                         │
│                                     │
│ Price near take-profit but still    │
│ holding based on technical signal   │
└─────────────────────────────────────┘
                │
                ▼
PHASE 6: EXIT EXECUTION
┌─────────────────────────────────────┐
│ Position Close                      │
├─────────────────────────────────────┤
│ Trigger: TIME LIMIT (2 hours)       │
│                                     │
│ Exit Details:                       │
│ • Exit price: $161.20               │
│ • Exit time: 14:30                  │
│ • Duration: 1h 45m                  │
│                                     │
│ P&L Calculation:                    │
│ • Gross: 5 × ($161.20 - $155.02)   │
│ • P&L: +$30.90 (+0.24% of capital)  │
│ • Fees: ~$1                         │
│ • Net P&L: +$29.90                  │
│                                     │
│ Log to Database:                    │
│ • Entry: $155.02 @ 12:45            │
│ • Exit: $161.20 @ 14:30             │
│ • Signal: OVERSOLD + BULLISH        │
│ • Reason: TIME_EXIT                 │
│ • P&L: +$29.90 (+4.01%)             │
│ • Win/Loss: WIN                     │
│                                     │
│ Position CLOSED                     │
└─────────────────────────────────────┘
                │
                ▼
PHASE 7: LOGGING & UPDATES
┌─────────────────────────────────────┐
│ Post-Trade Processing               │
├─────────────────────────────────────┤
│ 1. Update Dashboard                 │
│    • Closed trades count: 1         │
│    • Today's P&L: +$29.90           │
│    • Win rate: 50% (1W, 1L)         │
│                                     │
│ 2. Send Alerts                      │
│    • Trade closed successfully      │
│    • P&L: +$29.90                   │
│                                     │
│ 3. Update Daily Summary             │
│    • Trades today: 2                │
│    • Wins: 1, Losses: 1             │
│    • Daily P&L: +$29.90             │
│    • Daily Return: +0.04%           │
│                                     │
│ 4. Ready for next trade             │
│    • Open positions: 1              │
│    • Capital available: $80,529.90  │
│    • Can take 4 more concurrent     │
└─────────────────────────────────────┘


================================================================================
                    SYSTEM INTERACTION DIAGRAM
================================================================================

USER/DASHBOARD
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
   FLASK UI                             ALERTS
   ├─ View trades                       ├─ Email
   ├─ View metrics                      ├─ Console
   ├─ Start/Stop bot                    └─ Log files
   └─ Manual trades (optional)

       │
       ▼
   MAIN APPLICATION
   ├─ main.py (Orchestrator)
   │  ├─ Initialize all components
   │  ├─ Start main loop
   │  └─ Handle graceful shutdown
   │
   ├─────────────────────────────────────────────────────────┐
   │                                                         │
   ▼                                                         ▼
EVERY CYCLE (1-5 min)                        CONTINUOUS MONITORING
│                                            │
├─ TechnicalAnalyzer                        ├─ TradeManager
│  ├─ Fetch OHLCV from Alpaca              │  ├─ Check open positions
│  ├─ Calculate indicators                  │  ├─ Check stop-loss
│  └─ Generate signals                      │  ├─ Check take-profit
│                                           │  └─ Close if condition met
├─ DecisionEngine                           │
│  ├─ Evaluate signals                     ├─ RiskManager
│  ├─ Apply risk rules                      │  ├─ Monitor daily P&L
│  └─ Approve/Reject trades                │  ├─ Check position limits
│                                           │  └─ Enforce risk rules
├─ RiskManager                              │
│  ├─ Calculate position size               ├─ TradeLogger
│  ├─ Set stop-loss/take-profit            │  ├─ Log all changes
│  └─ Verify risk limits                    │  ├─ Update database
│                                           │  └─ Update dashboard
└─ Database
   ├─ Log indicators
   ├─ Log trades
   ├─ Update account history
   └─ Calculate performance


================================================================================
                        CONFIGURATION PYRAMID
================================================================================

                            APPLICATION
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            settings.py (LOGIC)         .env (SECRETS)
            
            ├─ Thresholds:              ├─ API Keys
            │  ├─ RSI: 30/70            │  ├─ APCA_API_KEY_ID
            │  ├─ MACD: 0.001           │  ├─ APCA_API_SECRET_KEY
            │  └─ BB: 2.0 std dev       │  └─ APCA_API_BASE_URL
            │                           │
            ├─ Risk Limits:             ├─ Email Config
            │  ├─ Daily loss: 12%       │  ├─ SMTP server
            │  ├─ Max trades: 5         │  └─ Email alerts
            │  └─ Max risk/trade: 1%    │
            │                           ├─ Database
            ├─ Trade Params:            │  └─ Connection string
            │  ├─ Stop-loss: 2×ATR      │
            │  ├─ Take-profit: 3×ATR    └─ Alpaca Mode
            │  └─ Max hold: 2 hours        ├─ paper (test)
            │                              └─ live (real money)
            └─ Watchlist
               └─ 50 stocks


================================================================================
                         ERROR HANDLING FLOW
================================================================================

ERROR OCCURS
       │
       ├─→ API ERROR (Alpaca connection)
       │   ├─ Retry with exponential backoff
       │   ├─ After 3 retries → Alert
       │   └─ After 5 retries → Halt trading
       │
       ├─→ DATA ERROR (Invalid OHLCV)
       │   ├─ Log error
       │   ├─ Skip that stock
       │   └─ Continue with others
       │
       ├─→ TRADE ERROR (Order rejected)
       │   ├─ Analyze rejection reason
       │   ├─ Log to database
       │   ├─ Alert user
       │   └─ Continue scanning
       │
       └─→ CRITICAL ERROR (Database down)
           ├─ Stop all trading
           ├─ Close all positions
           ├─ Send emergency alert
           └─ Require manual intervention


================================================================================


---
## DATA FLOW
### 1. INITIALIZATION FLOW

START │ ├─→ Load Configuration │ ├─ Load .env credentials │ ├─ Load settings (thresholds, limits) │ └─ Validate parameters │ ├─→ Connect to External Systems │ ├─ Alpaca API (Paper/Live Trading) │ ├─ Database (PostgreSQL/SQLite) │ └─ Verify connectivity │ ├─→ Initialize Components │ ├─ TechnicalAnalyzer │ ├─ DecisionEngine │ ├─ TradeManager │ ├─ RiskManager │ └─ TradeLogger │ └─→ Enter Main Loop



### 2. MAIN SCANNING CYCLE (Every 1-5 minutes)
SCAN CYCLE START │ ├─→ GET MARKET STATUS │ ├─ Check if market is open │ ├─ Get current time │ └─ Skip if market closed │ ├─→ GET ACCOUNT STATUS │ ├─ Fetch account balance │ ├─ Calculate available capital │ ├─ Check daily P&L │ └─ Verify trading permissions │ ├─→ SCAN WATCHLIST (50 stocks) │ │ │ └─→ FOR EACH STOCK: │ │ │ ├─→ FETCH PRICE DATA │ │ ├─ Get last 100 bars (daily or 5-min) │ │ ├─ Calculate OHLCV data │ │ └─ Store in memory │ │ │ ├─→ TECHNICAL ANALYSIS │ │ ├─ Calculate RSI (14 period) │ │ ├─ Calculate MACD (12,26,9) │ │ ├─ Calculate Bollinger Bands (20, 2σ) │ │ ├─ Calculate Stochastic RSI │ │ ├─ Calculate Volume Trend │ │ ├─ Calculate ATR │ │ ├─ Find Support/Resistance │ │ └─ Generate Trading Signal │ │ │ ├─→ SIGNAL GENERATION │ │ ├─ Combine all indicators │ │ ├─ Calculate confidence score (-100 to +100) │ │ └─ Determine: BUY / SELL / NEUTRAL │ │ │ ├─→ RISK ASSESSMENT │ │ ├─ Check daily loss limit │ │ ├─ Check max concurrent trades │ │ ├─ Check position size limits │ │ ├─ Calculate stop-loss level │ │ └─ Calculate take-profit level │ │ │ ├─→ DECISION MAKING │ │ ├─ Is signal strength > threshold? (40%) │ │ ├─ Is risk acceptable? │ │ ├─ Avoid duplicate trades? │ │ └─ Place trade? (YES/NO) │ │ │ └─→ IF TRADE SIGNAL: │ ├─ Calculate trade parameters │ ├─ Submit order to Alpaca │ ├─ Log trade to database │ ├─ Set stop-loss & take-profit │ └─ Add to active positions │ ├─→ MANAGE ACTIVE POSITIONS │ │ │ └─→ FOR EACH OPEN POSITION: │ ├─ Check current P&L │ ├─ Check if stop-loss hit │ ├─ Check if take-profit hit │ ├─ Check technical deterioration │ └─ Close position if needed │ └─→ SCAN CYCLE END



---
## CORE COMPONENTS
### 1. **API LAYER** (`api/alpaca_client.py`)
**Responsibility**: Interface with Alpaca Trading API
AlpacaClient ├── Authentication │ ├─ Load API credentials from .env │ ├─ Initialize REST connection │ └─ Handle auth errors │ ├── Market Data │ ├─ get_account() → Account balance, buying power │ ├─ get_clock() → Market open/close status │ ├─ get_bars(symbol, tf) → OHLCV data for charting │ ├─ get_latest_bar() → Current price │ ├─ get_latest_trade() → Last trade price │ └─ list_positions() → Current open positions │ ├── Order Management │ ├─ submit_order() → Place buy/sell order │ ├─ get_orders() → Fetch order history │ ├─ cancel_order() → Cancel pending order │ └─ close_position() → Close position immediately │ └── Error Handling ├─ Retry logic for failed API calls ├─ Handle rate limiting └─ Log all API errors



**Example Data Flow**:
Trading Bot │ └─→ alpaca.get_bars('AAPL', '5Min', limit=100) │ └─→ Alpaca REST API │ └─→ Returns: 100 5-minute bars with OHLCV



### 2. **TECHNICAL ANALYSIS ENGINE** (`core/technical_analyzer.py`)
**Responsibility**: Calculate all technical indicators
TechnicalAnalyzer ├── Price Action │ ├─ calculate_moving_averages() → SMA 5,10,20,50,200 + EMA 12,26 │ ├─ calculate_momentum() → Price momentum │ └─ calculate_roc() → Rate of change │ ├── Momentum Indicators │ ├─ calculate_rsi() → RSI (0-100 scale) │ │ ├─ Threshold: > 70 = overbought │ │ └─ Threshold: < 30 = oversold │ │ │ ├─ calculate_macd() → MACD + Signal + Histogram │ │ ├─ Fast EMA: 12 period │ │ ├─ Slow EMA: 26 period │ │ ├─ Signal: 9 period MACD EMA │ │ └─ Histogram: MACD - Signal │ │ │ └─ calculate_stochastic_rsi() → Stochastic RSI (0-1 scale) │ ├─ Threshold: > 0.8 = overbought │ └─ Threshold: < 0.2 = oversold │ ├── Volatility Indicators │ ├─ calculate_bollinger_bands() → Upper/Middle/Lower bands │ │ ├─ Middle: 20-period SMA │ │ ├─ Bands: ±2 standard deviations │ │ └─ Signal: Price near upper/lower band │ │ │ └─ calculate_atr() → Average True Range (volatility) │ ├── Volume Analysis │ ├─ calculate_obv() → On-Balance Volume (buying pressure) │ └─ calculate_volume_trend() → Volume increasing/decreasing │ ├── Support & Resistance │ └─ find_support_resistance() → Key price levels │ ├─ Pivot point │ ├─ Support levels (2) │ └─ Resistance levels (2) │ └── Signal Generation └─ generate_trading_signal() → Combined signal ├─ Weighs all indicators ├─ Calculates confidence (-100 to +100) └─ Returns: BUY/SELL/NEUTRAL



**Example Calculation**:
Input: AAPL prices [150, 151, 149, 152, 153, ...]

RSI Calculation:

Calculate price changes: [+1, -2, +3, +1, ...]
Separate gains and losses
Calculate 14-period average gain/loss
RS = avg_gain / avg_loss
RSI = 100 - (100 / (1 + RS)) Output: RSI = 65.3 → NEUTRAL signal
MACD Calculation:

Calculate 12-period EMA: 151.4
Calculate 26-period EMA: 150.8
MACD = 151.4 - 150.8 = +0.6
Signal = 9-period EMA of MACD = +0.4
Histogram = 0.6 - 0.4 = +0.2 Output: BULLISH (MACD > Signal and positive histogram)
Final Signal Generation: RSI Score: +0 (neutral) MACD Score: +40 (bullish) BB Score: 0 (inside bands) Volume Score: +25 (increasing) MA Score: +30 (bullish crossover) ─────────────────── Total: +95 / 5 = 19% confidence Signal: NEUTRAL (< 40% threshold)



### 3. **DECISION ENGINE** (`core/decision_engine.py`)
**Responsibility**: Make trading decisions based on analysis
DecisionEngine ├── Signal Analysis │ ├─ Technical signal: BUY/SELL/NEUTRAL │ ├─ Signal strength: confidence score │ ├─ Signal quality: number of confirming indicators │ └─ Time-based filters: avoid trading near market close │ ├── Risk Assessment │ ├─ Calculate position size (Kelly criterion or fixed %) │ ├─ Determine stop-loss level (% or ATR-based) │ ├─ Determine take-profit level (risk/reward ratio) │ ├─ Check daily loss limit │ ├─ Check max concurrent trades limit │ └─ Verify account has sufficient capital │ ├── Trade Filtering │ ├─ Avoid duplicate signals (cooldown period) │ ├─ Avoid trading illiquid stocks │ ├─ Avoid trading on earnings day │ ├─ Check recent trade history │ └─ Pattern day trader rule compliance │ ├── Trade Approval │ ├─ All risk checks passed? → APPROVE │ ├─ Any risk limit exceeded? → REJECT │ └─ Manual override available? (optional) │ └── Trade Parameters ├─ Symbol: AAPL ├─ Side: BUY/SELL ├─ Quantity: 10 shares ├─ Type: MARKET or LIMIT ├─ Stop Loss: $150 ├─ Take Profit: $158 ├─ Expected Risk: $80 (quantity × stop distance) └─ Expected Reward: $80 (1:1 ratio)



**Decision Logic**:
```python
def should_trade(stock, signal):
    # 1. Check if signal is strong enough
    if signal.confidence < 40:
        return False  # Signal too weak
    
    # 2. Check risk limits
    if daily_loss >= daily_loss_limit:
        return False  # Daily loss limit hit
    
    if open_positions >= max_concurrent_trades:
        return False  # Too many open trades
    
    # 3. Check if stock is suitable
    if volume < MIN_VOLUME:
        return False  # Stock too illiquid
    
    # 4. Check for duplicate signals (cooldown)
    if last_trade_time < 30_minutes_ago:
        return False  # Too recent
    
    # 5. Check account capital
    required_capital = position_size * entry_price
    if available_capital < required_capital:
        return False  # Insufficient capital
    
    # 6. All checks passed
    return True


4. TRADE MANAGEMENT (core/trade_manager.py)
Responsibility: Execute and manage trades

TradeManager
├── Order Placement
│   ├─ Submit order to Alpaca
│   ├─ Handle order confirmation
│   ├─ Store order ID
│   └─ Log order details
│
├── Position Tracking
│   ├─ Track open positions
│   ├─ Update position prices
│   ├─ Calculate P&L
│   └─ Monitor stop-loss & take-profit
│
├── Exit Management
│   ├─ Monitor for stop-loss hit
│   ├─ Monitor for take-profit hit
│   ├─ Monitor for technical deterioration
│   ├─ Time-based exits (max hold time)
│   └─ Close position when condition met
│
└── Error Handling
    ├─ Retry failed orders
    ├─ Handle partial fills
    ├─ Handle order rejections
    └─ Emergency close position



5. RISK MANAGEMENT (core/risk_manager.py)
Responsibility: Enforce risk controls

RiskManager
├── Position Sizing
│   ├─ Calculate max shares based on account
│   ├─ Apply Kelly criterion or fixed percentage
│   ├─ Limit per-trade risk to 1-2% of capital
│   └─ Limit position to max 5% of capital
│
├── Daily Limits
│   ├─ Track daily P&L
│   ├─ Stop trading if daily loss > limit (e.g., 12%)
│   ├─ Reset daily limits at market close
│   └─ Log daily performance
│
├── Concurrent Trade Limits
│   ├─ Max 5 concurrent trades
│   ├─ Spread trades across different sectors
│   ├─ Avoid clustering in same price range
│   └─ Monitor correlation
│
├── Stop-Loss & Take-Profit
│   ├─ Calculate based on ATR (2 × ATR)
│   ├─ Or fixed percentage (2% stop, 3% profit)
│   ├─ Risk/Reward ratio minimum 1:1.5
│   └─ Trailing stop option
│
└── Compliance
    ├─ Pattern day trader rule (3+ day trades per 5 days)
    ├─ Margin requirements
    ├─ Account value protection
    └─ Regulatory compliance

6. DATABASE LAYER (storage/database.py)
Responsibility: Persist data

Database
├── Schema
│   ├─ trades table
│   │   ├─ id, timestamp, symbol, side
│   │   ├─ entry_price, quantity
│   │   ├─ exit_price, exit_time
│   │   ├─ pnl, pnl_percent
│   │   ├─ stop_loss, take_profit
│   │   ├─ reason (exit reason)
│   │   └─ technical_signal
│   │
│   ├─ indicators table
│   │   ├─ id, timestamp, symbol
│   │   ├─ rsi, macd, bb_signal
│   │   ├─ volume_trend, support
│   │   └─ resistance
│   │
│   ├─ account_history table
│   │   ├─ id, timestamp
│   │   ├─ balance, equity
│   │   ├─ buying_power, daily_pnl
│   │   └─ open_positions_count
│   │
│   └─ daily_summary table
│       ├─ date, total_trades
│       ├─ wins, losses
│       ├─ daily_pnl, daily_pnl_percent
│       └─ largest_win, largest_loss
│
├── Operations
│   ├─ log_trade()
│   ├─ update_trade()
│   ├─ log_indicator()
│   ├─ get_trade_history()
│   ├─ calculate_performance()
│   └─ get_daily_summary()
│
└── Queries
    ├─ Total trades today
    ├─ Win rate
    ├─ Average win/loss
    ├─ Best/worst trade
    └─ Performance by symbol

7. MONITORING LAYER (monitoring/)
Responsibility: Logging and dashboard



TradeLogger
├── Trade Logging
│   ├─ Entry: Time, Symbol, Price, Quantity, Reason
│   ├─ Exit: Time, Price, P&L, Reason
│   ├─ Metrics: Win rate, Avg win/loss, Sharpe ratio
│   └─ Daily: Summary, Performance, Statistics
│
└── Output
    ├─ Console logging
    ├─ File logging (trades.log, errors.log)
    ├─ Database persistence
    └─ Dashboard real-time updates
Dashboard (Flask)
├── Real-time Metrics
│   ├─ Current account balance
│   ├─ Open positions (P&L)
│   ├─ Daily P&L
│   ├─ Win rate
│   └─ Last 5 trades
│
├── Charts
│   ├─ Price chart with technical indicators
│   ├─ P&L over time
│   ├─ Win/Loss distribution
│   └─ Monthly performance
│
└── Alerts
    ├─ Trade placed
    ├─ Trade closed
    ├─ Daily loss limit hit
    ├─ Error conditions
    └─ System status

TECHNICAL ANALYSIS ENGINE - DETAILED
Signal Scoring System


SIGNAL SCORING (Each indicator contributes points)
┌─────────────────────────────────────────────────────────┐
│ INDICATOR         │ BULLISH SCORE │ BEARISH SCORE       │
├─────────────────────────────────────────────────────────┤
│ RSI               │               │                     │
│ - Very Oversold   │ +75           │ N/A                 │
│ - Oversold        │ +50           │ N/A                 │
│ - Overbought      │ N/A           │ -50                 │
│ - Very Overbought │ N/A           │ -75                 │
│                   │               │                     │
│ MACD              │               │                     │
│ - Bullish Cross   │ +40           │ N/A                 │
│ - Bullish Trend   │ +40           │ N/A                 │
│ - Bearish Cross   │ N/A           │ -40                 │
│ - Bearish Trend   │ N/A           │ -40                 │
│                   │               │                     │
│ Bollinger Bands   │               │                     │
│ - Near Lower      │ +30           │ N/A                 │
│ - Near Upper      │ N/A           │ -30                 │
│ - Inside Bands    │ 0             │ 0                   │
│                   │               │                     │
│ Volume            │               │                     │
│ - Increasing      │ +25           │ N/A                 │
│ - Stable          │ 0             │ 0                   │
│ - Decreasing      │ N/A           │ -25                 │
│                   │               │                     │
│ MA Crossover      │               │                     │
│ - Bullish (50>200)│ +30           │ N/A                 │
│ - Bearish (50<200)│ N/A           │ -30                 │
│ - Neutral         │ 0             │ 0                   │
└─────────────────────────────────────────────────────────┘
FINAL CALCULATION:
  Confidence = (Sum of all scores) / (Number of indicators)
  
  Example:
    RSI: +50 (oversold)
    MACD: +40 (bullish)
    BB: 0 (inside)
    Volume: +25 (increasing)
    MA: +30 (bullish)
    ─────────
    Total: +145 / 5 = 29% confidence
  
  INTERPRETATION:
    > 40% = BUY signal (moderate strength)
    < -40% = SELL signal (moderate strength)
    -40% to +40% = NEUTRAL (conflicting signals)


Indicator Thresholds (from settings.py)


RSI_OVERBOUGHT = 70           ← Selling pressure building
RSI_OVERSOLD = 30             ← Buying opportunity
RSI_VERY_OVERBOUGHT = 80      ← Extreme selling
RSI_VERY_OVERSOLD = 20        ← Extreme buying opportunity
MACD_DIVERGENCE_THRESHOLD = 0.001    ← Minimum histogram to confirm trend
STOCH_RSI_THRESHOLD = 0.20    ← Oversold/Overbought boundary
                               ← Oversold: < 0.2, Overbought: > 0.8
BB_STDDEV = 2.0                ← Number of standard deviations
                                ← Price 2σ away = extreme move
MIN_DAILY_VOLUME_MULTIPLIER = 0.5   ← Volume must be 50% of average


DECISION ENGINE - DETAILED
Trade Approval Workflow


TRADE REQUEST
  │
  ├─→ SIGNAL VALIDATION
  │   ├─ Confidence > 40%? ✓
  │   ├─ Signal type: BUY/SELL? ✓
  │   └─ Multiple confirming indicators? ✓
  │
  ├─→ RISK VALIDATION
  │   ├─ Daily loss < limit? ✓
  │   ├─ Open positions < max? ✓
  │   ├─ Capital available? ✓
  │   └─ Position size acceptable? ✓
  │
  ├─→ STOCK VALIDATION
  │   ├─ Volume > minimum? ✓
  │   ├─ Bid-ask spread < limit? ✓
  │   ├─ Not on earnings day? ✓
  │   └─ Not in volatile news? ✓
  │
  ├─→ DUPLICATE CHECK
  │   ├─ Recent trade on same symbol? ✗
  │   ├─ Cooldown period active? ✗
  │   └─ Can trade same symbol again? ✓
  │
  ├─→ PATTERN DAY TRADER CHECK
  │   ├─ Account value >= \$25,000? ✓
  │   ├─ Day trades in last 5 days? (Count: 2)
  │   └─ Can do 1 more today? ✓
  │
  └─→ FINAL DECISION
      ALL CHECKS PASSED → EXECUTE TRADE
      
      Trade Parameters:
      - Symbol: AAPL
      - Side: BUY
      - Quantity: 10 shares @ \$155
      - Entry: \$1,550
      - Stop Loss: \$150 (2% below entry)
      - Take Profit: \$165 (1% above entry)
      - Risk: \$50 (10 × \$5)
      - Reward: \$100 (10 × \$10)
      - Risk/Reward: 1:2 ✓

Position Management Workflow

POSITION OPEN (AAPL 10 shares @ \$155)
  │
  ├─→ EVERY MINUTE CHECK:
  │   │
  │   ├─ Current price: $156.50
  │   ├─ Unrealized P&L: +$15 (+0.97%)
  │   │
  │   ├─→ STOP-LOSS CHECK
  │   │   └─ Is price < \$150? NO → Continue
  │   │
  │   ├─→ TAKE-PROFIT CHECK
  │   │   └─ Is price > \$165? NO → Continue
  │   │
  │   ├─→ TECHNICAL DETERIORATION CHECK
  │   │   ├─ RSI went overbought? NO
  │   │   ├─ MACD turned bearish? NO
  │   │   └─ Continue holding
  │   │
  │   └─→ TIME-BASED EXIT CHECK
  │       ├─ Time held: 45 minutes
  │       ├─ Max hold time: 2 hours
  │       └─ Continue holding
  │
  ├─→ AFTER 1 HOUR 30 MINUTES
  │   │
  │   ├─ Current price: $157.25
  │   ├─ P&L: +$22.50 (+1.45%)
  │   │
  │   └─→ TAKE-PROFIT HIT
  │       ├─ Price > \$165? NO, but near
  │       ├─ Technical signal? STILL BULLISH
  │       └─ Hold for more profit
  │
  └─→ AFTER 2 HOURS
      │
      ├─ Current price: $158.75
      ├─ P&L: +$37.50 (+2.42%)
      │
      └─→ TIME-BASED EXIT TRIGGERED
          ├─ Max hold time (2 hours) reached
          ├─ Close position immediately
          ├─ Exit price: $158.75
          ├─ Realized P&L: +$37.50 (+2.42%)
          ├─ Reason: TIME_EXIT
          └─ Position CLOSED


TRADE EXECUTION FLOW
Complete Trade Lifecycle


┌─────────────────────────────────────────────────────────────┐
│ STEP 1: SIGNAL GENERATION (Technical Analysis)              │
└─────────────────────────────────────────────────────────────┘
   Input: AAPL prices [150, 151, 149, 152, ...]
   Process:
   - Calculate 100+ data points
   - Analyze 5 different indicators
   - Score signal strength
   Output: Signal = BUY, Confidence = 65%

┌─────────────────────────────────────────────────────────────┐
│ STEP 2: RISK ASSESSMENT                                     │
└─────────────────────────────────────────────────────────────┘
   Inputs:
   - Account balance: \$80,508
   - Capital per trade: \$4,025
   - ATR: \$2.15
   - Daily loss limit: 12% = \$9,661
   
   Calculations:
   - Entry price: \$155
   - Stop loss: \$155 - (2 × \$2.15) = \$150.70
   - Take profit: \$155 + (1.5 × 2 × \$2.15) = \$161.45
   - Position size: \$4,025 / $155 = 26 shares
   - Risk per trade: 26 × ($155 - \$150.70) = $112
   - Reward: 26 × ($161.45 - \$155) = $167
   
   Output: Risk/Reward = 1:1.5 ✓

┌─────────────────────────────────────────────────────────────┐
│ STEP 3: DECISION ENGINE                                     │
└─────────────────────────────────────────────────────────────┘
   Checks:
   ☑ Signal confidence > 40%? (65% > 40%)
   ☑ Daily loss limit not exceeded? ($0 < \$9,661)
   ☑ Open positions < 5? (2 < 5)
   ☑*
