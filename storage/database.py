import sqlite3
import logging
from datetime import datetime
from pathlib import Path
logger = logging.getLogger(__name__)
class Database:
    """SQLite database manager for trade data."""
    
    def __init__(self, db_path: str = "data/trades.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._init_connection()
        self._init_db()
    
    def _init_connection(self):
        """Initialize database connection."""
        try:
            Path("data").mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Database connected: {self.db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _init_db(self):
        """Initialize database tables."""
        try:
            # Create tables
            self._create_tables()
            self.conn.commit()
            logger.info("[Ok] Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_tables(self):
        """Create all required tables."""
        
        # Entries table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL,
                option_type TEXT,
                strike REAL,
                expiration TEXT,
                contracts INTEGER,
                entry_price REAL,
                capital_used REAL,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)
        
        # Exits table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS exits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                exit_price REAL NOT NULL,
                exit_reason TEXT,
                contracts_closed INTEGER,
                pnl_dollars REAL,
                pnl_percent REAL,
                FOREIGN KEY (entry_id) REFERENCES entries(id)
            )
        """)
        
        # Closed trades table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS closed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                signal TEXT,
                entry_date TEXT,
                entry_price REAL,
                exit_date TEXT,
                exit_price REAL,
                contracts INTEGER,
                hold_days INTEGER,
                pnl_dollars REAL,
                pnl_percent REAL,
                win_loss TEXT,
                exit_reason TEXT,
                FOREIGN KEY (entry_id) REFERENCES entries(id)
            )
        """)
        
        # Daily stats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_pnl_dollars REAL DEFAULT 0,
                total_pnl_percent REAL DEFAULT 0,
                max_loss REAL DEFAULT 0,
                max_gain REAL DEFAULT 0,
                avg_trade_duration REAL DEFAULT 0
            )
        """)
        
        # Ticker stats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticker_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                trades_count INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                UNIQUE(ticker, date)
            )
        """)
        
        # Create indexes
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_ticker 
            ON entries(ticker)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_timestamp 
            ON entries(timestamp)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exits_entry_id 
            ON exits(entry_id)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_closed_trades_ticker 
            ON closed_trades(ticker)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_closed_trades_date 
            ON closed_trades(entry_date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_stats_date 
            ON daily_stats(date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker_stats_ticker 
            ON ticker_stats(ticker)
        """)
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def insert_entry(self, **kwargs) -> int:
        """Insert a new entry record."""
        try:
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?' for _ in kwargs])
            query = f"INSERT INTO entries ({keys}) VALUES ({placeholders})"
            
            self.cursor.execute(query, tuple(kwargs.values()))
            self.conn.commit()
            
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting entry: {e}")
            self.conn.rollback()
            raise
    
    def insert_exit(self, **kwargs) -> int:
        """Insert a new exit record."""
        try:
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?' for _ in kwargs])
            query = f"INSERT INTO exits ({keys}) VALUES ({placeholders})"
            
            self.cursor.execute(query, tuple(kwargs.values()))
            self.conn.commit()
            
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting exit: {e}")
            self.conn.rollback()
            raise
    
    def insert_closed_trade(self, **kwargs) -> int:
        """Insert a closed trade record."""
        try:
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?' for _ in kwargs])
            query = f"INSERT INTO closed_trades ({keys}) VALUES ({placeholders})"
            
            self.cursor.execute(query, tuple(kwargs.values()))
            self.conn.commit()
            
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting closed trade: {e}")
            self.conn.rollback()
            raise
    
    def insert_daily_stats(self, **kwargs):
        """Insert or update daily stats."""
        try:
            date = kwargs.get('date')
            
            # Check if exists
            self.cursor.execute("SELECT id FROM daily_stats WHERE date = ?", (date,))
            exists = self.cursor.fetchone()
            
            if exists:
                # Update
                set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys() if k != 'date'])
                values = [v for k, v in kwargs.items() if k != 'date']
                values.append(date)
                
                query = f"UPDATE daily_stats SET {set_clause} WHERE date = ?"
                self.cursor.execute(query, values)
            else:
                # Insert
                keys = ', '.join(kwargs.keys())
                placeholders = ', '.join(['?' for _ in kwargs])
                query = f"INSERT INTO daily_stats ({keys}) VALUES ({placeholders})"
                self.cursor.execute(query, tuple(kwargs.values()))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting daily stats: {e}")
            self.conn.rollback()
            raise
    
    def get_entries(self, limit: int = None) -> list:
        """Get all entries."""
        try:
            query = "SELECT * FROM entries ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching entries: {e}")
            return []
    
    def get_entry_by_id(self, entry_id: int):
        """Get entry by ID."""
        try:
            self.cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching entry: {e}")
            return None
    
    def get_active_entries(self) -> list:
        """Get all active (open) entries."""
        try:
            self.cursor.execute(
                "SELECT * FROM entries WHERE status = 'ACTIVE' ORDER BY timestamp DESC"
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching active entries: {e}")
            return []
    
    def update_entry_status(self, entry_id: int, status: str):
        """Update entry status."""
        try:
            self.cursor.execute(
                "UPDATE entries SET status = ? WHERE id = ?",
                (status, entry_id)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating entry status: {e}")
            self.conn.rollback()
            raise
    
    def get_closed_trades(self, limit: int = None) -> list:
        """Get all closed trades."""
        try:
            query = "SELECT * FROM closed_trades ORDER BY entry_date DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching closed trades: {e}")
            return []
    
    def get_daily_stats(self, date: str):
        """Get stats for a specific date."""
        try:
            self.cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching daily stats: {e}")
            return None
    
    def get_ticker_stats(self, ticker: str, date: str):
        """Get stats for a ticker on a specific date."""
        try:
            self.cursor.execute(
                "SELECT * FROM ticker_stats WHERE ticker = ? AND date = ?",
                (ticker, date)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching ticker stats: {e}")
            return None
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()