"""
SQLite database layer for earnings copilot system.
Handles all database operations and schema creation.
"""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
import aiosqlite


DATABASE_PATH = "earnings_copilot.db"


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()


# Global database manager instance
db_manager = DatabaseManager()


async def init_db():
    """Initialize database with required tables."""
    async with db_manager.get_connection() as conn:
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL CHECK (role IN ('ADMIN','TRADER'))
            )
        """)
        
        # Subscriptions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                channels TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, ticker)
            )
        """)
        
        # Documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                period TEXT,
                doc_type TEXT NOT NULL,
                path TEXT NOT NULL,
                uploader TEXT NOT NULL,
                received_at TEXT NOT NULL
            )
        """)
        
        # Compliance rules table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_rules (
                rule_id TEXT PRIMARY KEY,
                scope_class TEXT,
                scope_tickers TEXT,
                initial_margin REAL,
                maintenance_margin REAL,
                effective_date TEXT,
                provenance TEXT,
                confidence REAL
            )
        """)
        
        # Signals cache table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                ticker TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for better performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_ticker ON subscriptions(ticker)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents(ticker)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_compliance_effective_date ON compliance_rules(effective_date)")
        
        await conn.commit()


# Document operations
async def add_document(doc_id: str, ticker: str, period: Optional[str], 
                      doc_type: str, path: str, uploader: str) -> bool:
    """Add a new document record."""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT INTO documents (doc_id, ticker, period, doc_type, path, uploader, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, ticker, period, doc_type, path, uploader, datetime.utcnow().isoformat()))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error adding document: {e}")
        return False


async def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# Subscription operations
async def add_subscription(user_id: str, ticker: str, channels: List[str]) -> bool:
    """Add or update subscription."""
    try:
        async with db_manager.get_connection() as conn:
            channels_csv = ",".join(channels)
            await conn.execute("""
                INSERT OR REPLACE INTO subscriptions (user_id, ticker, channels, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, ticker, channels_csv, datetime.utcnow().isoformat()))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error adding subscription: {e}")
        return False


async def remove_subscription(user_id: str, ticker: str) -> bool:
    """Remove subscription."""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                DELETE FROM subscriptions WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error removing subscription: {e}")
        return False


async def list_subscriptions(user_id: str) -> List[Dict[str, Any]]:
    """List all subscriptions for a user."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            sub = dict(row)
            sub['channels'] = sub['channels'].split(',') if sub['channels'] else []
            result.append(sub)
        return result


async def subscribers_for_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Get all subscribers for a specific ticker."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM subscriptions WHERE ticker = ?
        """, (ticker,))
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            sub = dict(row)
            sub['channels'] = sub['channels'].split(',') if sub['channels'] else []
            result.append(sub)
        return result


# Compliance rules operations
async def add_compliance_rule(rule_id: str, scope_class: Optional[str], 
                            scope_tickers: List[str], initial_margin: float,
                            maintenance_margin: float, effective_date: str,
                            provenance: Dict[str, Any], confidence: float) -> bool:
    """Add compliance rule."""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO compliance_rules 
                (rule_id, scope_class, scope_tickers, initial_margin, maintenance_margin, 
                 effective_date, provenance, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (rule_id, scope_class, ",".join(scope_tickers), initial_margin,
                  maintenance_margin, effective_date, json.dumps(provenance), confidence))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error adding compliance rule: {e}")
        return False


async def get_compliance_rules_for_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Get compliance rules affecting a ticker."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM compliance_rules 
            WHERE scope_tickers LIKE ? OR scope_class IS NOT NULL
            ORDER BY effective_date DESC
        """, (f"%{ticker}%",))
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            rule = dict(row)
            rule['scope_tickers'] = rule['scope_tickers'].split(',') if rule['scope_tickers'] else []
            rule['provenance'] = json.loads(rule['provenance']) if rule['provenance'] else {}
            result.append(rule)
        return result


# Signal operations
async def upsert_signal(ticker: str, payload: Dict[str, Any]) -> bool:
    """Update or insert signal for ticker."""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO signals (ticker, payload, updated_at)
                VALUES (?, ?, ?)
            """, (ticker, json.dumps(payload), datetime.utcnow().isoformat()))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error upserting signal: {e}")
        return False


async def get_signal(ticker: str) -> Optional[Dict[str, Any]]:
    """Get latest signal for ticker."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT payload FROM signals WHERE ticker = ?
        """, (ticker,))
        row = await cursor.fetchone()
        if row:
            return json.loads(row['payload'])
        return None


# User operations
async def add_user(user_id: str, role: str) -> bool:
    """Add user with role."""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO users (id, role) VALUES (?, ?)
            """, (user_id, role))
            await conn.commit()
            return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False


async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# Initialize database on module import
def init_db_sync():
    """Synchronous database initialization for CLI usage."""
    import asyncio
    asyncio.run(init_db())


if __name__ == "__main__":
    init_db_sync()
    print("Database initialized successfully!")
