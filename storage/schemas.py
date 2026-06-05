"""
storage/schemas.py - Database table schemas
Defines the structure of all database tables
"""

# Entry Events Schema
ENTRIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ticker TEXT NOT NULL,
    option_type TEXT NOT NULL,
    strike REAL NOT NULL,
    dte INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    contracts INTEGER NOT NULL,
    position_cost REAL NOT NULL,
    
    -- Market context
    stock_price REAL,
    rsi REAL,
    iv REAL,
    iv_percentile REAL,
    vix REAL,
    
    -- Decision context
    confidence REAL,
    reason TEXT,
    
    -- Indexes for fast queries
    INDEX idx_ticker (ticker),
    INDEX idx_timestamp (timestamp),
    INDEX idx_trade_id (trade_id)
);
"""

# Exit Events Schema
EXITS_SCHEMA = """
CREATE TABLE IF NOT EXISTS exits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ticker TEXT NOT NULL,
    exit_reason TEXT NOT NULL,
    exit_trigger TEXT,
    exit_price REAL NOT NULL,
    exit_qty INTEGER NOT NULL,
    pnl_dollars REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    
    FOREIGN KEY (trade_id) REFERENCES entries(trade_id),
    INDEX idx_trade_id (trade_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_exit_reason (exit_reason)
);
"""

# Closed Trades Schema (Entry + Exit combined)
TRADES_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,
    
    -- Entry info
    entry_timestamp DATETIME NOT NULL,
    entry_price REAL NOT NULL,
    entry_qty INTEGER NOT NULL,
    entry_cost REAL NOT NULL,
    
    -- Exit info
    exit_timestamp DATETIME NOT NULL,
    exit_price REAL NOT NULL,
    exit_qty INTEGER NOT NULL,
    exit_proceeds REAL NOT NULL,
    exit_reason TEXT NOT NULL,
    
    -- Position info
    ticker TEXT NOT NULL,
    option_type TEXT NOT NULL,
    strike REAL NOT NULL,
    entry_dte INTEGER NOT NULL,
    
    -- P&L
    pnl_dollars REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    profitable INTEGER NOT NULL,
    
    -- Timing
    hold_days INTEGER NOT NULL,
    hold_hours REAL NOT NULL,
    
    -- Market context
    entry_iv REAL,
    exit_iv REAL,
    entry_rsi REAL,
    entry_vix REAL,
    
    -- Status
    status TEXT DEFAULT 'CLOSED',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ticker (ticker),
    INDEX idx_entry_timestamp (entry_timestamp),
    INDEX idx_exit_timestamp (exit_timestamp),
    INDEX idx_profitable (profitable),
    INDEX idx_trade_id (trade_id)
);
"""

# Daily Performance Schema
DAILY_PERFORMANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    
    -- Trading stats
    trades_opened INTEGER DEFAULT 0,
    trades_closed INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    
    -- P&L
    total_pnl_dollars REAL DEFAULT 0,
    total_pnl_pct REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_win REAL DEFAULT 0,
    avg_loss REAL DEFAULT 0,
    
    -- Capital
    starting_capital REAL,
    ending_capital REAL,
    max_drawdown REAL DEFAULT 0,
    
    -- Positions
    peak_concurrent_positions INTEGER DEFAULT 0,
    
    INDEX idx_date (date)
);
"""

# Ticker Performance Schema (for historical context)
TICKER_PERFORMANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticker_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    
    -- Stats
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    
    -- P&L
    total_pnl_dollars REAL DEFAULT 0,
    total_pnl_pct REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_win REAL DEFAULT 0,
    avg_loss REAL DEFAULT 0,
    
    -- Greeks context
    best_performance_iv_percentile REAL,
    best_performance_rsi_range TEXT,
    
    -- Updated
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(ticker),
    INDEX idx_ticker (ticker)
);
"""

# Trade Journal Schema (for notes & analysis)
TRADE_JOURNAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    entry_type TEXT NOT NULL,  -- 'ENTRY_NOTE', 'PRICE_UPDATE', 'DECISION', 'REVIEW'
    notes TEXT,
    
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id),
    INDEX idx_trade_id (trade_id)
);
"""

# All schemas
ALL_SCHEMAS = [
    ENTRIES_SCHEMA,
    EXITS_SCHEMA,
    TRADES_SCHEMA,
    DAILY_PERFORMANCE_SCHEMA,
    TICKER_PERFORMANCE_SCHEMA,
    TRADE_JOURNAL_SCHEMA,
]
