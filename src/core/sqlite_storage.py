"""
SQLite storage adapter for demo/development
Mimics PostgreSQL interface for compatibility
"""

import sqlite3
import json
from typing import Dict, Any, List, Optional
import asyncio
from contextlib import asynccontextmanager

class SQLiteStorage:
    """SQLite storage adapter with PostgreSQL-like interface"""
    
    def __init__(self, db_path: str = "conceptdb.db"):
        self.db_path = db_path
        self.connection = None
        
    async def connect(self):
        """Connect to SQLite database"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        await self._create_tables()
        
    async def _create_tables(self):
        """Create necessary tables"""
        cursor = self.connection.cursor()
        
        # Create products table for demo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL,
                description TEXT
            )
        """)
        
        # Create concepts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create query_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                routing TEXT,
                response_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert demo data if empty
        cursor.execute("SELECT COUNT(*) as count FROM products")
        if cursor.fetchone()['count'] == 0:
            demo_products = [
                (1, "MacBook Pro", "Laptop", 2999, "Professional laptop for developers"),
                (2, "iPhone 15", "Phone", 999, "Latest smartphone with AI features"),
                (3, "AirPods Pro", "Audio", 249, "Noise-canceling wireless earbuds"),
                (4, "iPad Pro", "Tablet", 1099, "Powerful tablet for creative work"),
                (5, "Apple Watch", "Wearable", 399, "Smart watch with health tracking")
            ]
            cursor.executemany(
                "INSERT INTO products (id, name, category, price, description) VALUES (?, ?, ?, ?, ?)",
                demo_products
            )
        
        self.connection.commit()
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SQL query"""
        cursor = self.connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Handle different query types
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select'):
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        elif query_lower.startswith(('insert', 'update', 'delete')):
            self.connection.commit()
            return [{"affected_rows": cursor.rowcount}]
        else:
            self.connection.commit()
            return [{"success": True}]
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            return True
        except:
            return False
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    async def create_table(self, table_name: str, schema: Dict[str, str]):
        """Create a new table"""
        columns = []
        for col_name, col_type in schema.items():
            # Map PostgreSQL types to SQLite
            sqlite_type = col_type.upper()
            if 'VARCHAR' in sqlite_type or 'TEXT' in sqlite_type:
                sqlite_type = 'TEXT'
            elif 'INT' in sqlite_type:
                sqlite_type = 'INTEGER'
            elif 'FLOAT' in sqlite_type or 'DECIMAL' in sqlite_type:
                sqlite_type = 'REAL'
            elif 'BOOL' in sqlite_type:
                sqlite_type = 'INTEGER'
            
            columns.append(f"{col_name} {sqlite_type}")
        
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        await self.execute_query(query)
    
    async def insert_data(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into table"""
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['?' for _ in values])
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        result = await self.execute_query(query, tuple(values))
        
        return {"success": True, "id": self.connection.lastrowid}
    
    async def log_query(self, query: str, routing: str, response_time: float):
        """Log query execution"""
        await self.execute_query(
            "INSERT INTO query_logs (query, routing, response_time) VALUES (?, ?, ?)",
            (query, routing, response_time)
        )