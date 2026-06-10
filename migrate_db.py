#!/usr/bin/env python
"""
Migration script for snooker_auto upgrades.
Adds new tables and columns while preserving existing data.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "snooker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def column_exists(conn, table, column):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def table_exists(conn, table):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None

def run_migration():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_conn()
    
    # Create new tables if they don't exist
    # Ingredients table
    if not table_exists(conn, 'ingredients'):
        conn.execute("""
            CREATE TABLE ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT DEFAULT 'pcs',
                current_stock REAL DEFAULT 0,
                min_threshold REAL DEFAULT 10,
                vendor_id INTEGER,
                FOREIGN KEY (vendor_id) REFERENCES vendors(id)
            )
        """)
        print("✓ Created ingredients table")
    
    # Recipe ingredients junction table
    if not table_exists(conn, 'recipe_ingredients'):
        conn.execute("""
            CREATE TABLE recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
            )
        """)
        print("✓ Created recipe_ingredients table")
    
    # Vendors table
    if not table_exists(conn, 'vendors'):
        conn.execute("""
            CREATE TABLE vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                lead_time_days INTEGER DEFAULT 1,
                last_order_date TEXT,
                notes TEXT
            )
        """)
        print("✓ Created vendors table")
    
    # Combos table
    if not table_exists(conn, 'combos'):
        conn.execute("""
            CREATE TABLE combos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                discount_amount REAL DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                is_suggested INTEGER DEFAULT 0,
                time_of_day TEXT,
                description TEXT
            )
        """)
        print("✓ Created combos table")
    
    # Combo items junction table
    if not table_exists(conn, 'combo_items'):
        conn.execute("""
            CREATE TABLE combo_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                combo_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (combo_id) REFERENCES combos(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        print("✓ Created combo_items table")
    
    # Extend products table with stock columns
    if not column_exists(conn, 'products', 'current_stock'):
        conn.execute("ALTER TABLE products ADD COLUMN current_stock REAL DEFAULT 999")
        print("✓ Added current_stock column to products")
    
    if not column_exists(conn, 'products', 'min_stock_threshold'):
        conn.execute("ALTER TABLE products ADD COLUMN min_stock_threshold REAL DEFAULT 10")
        print("✓ Added min_stock_threshold column to products")
    
    if not column_exists(conn, 'products', 'stock_unit'):
        conn.execute("ALTER TABLE products ADD COLUMN stock_unit TEXT DEFAULT 'pcs'")
        print("✓ Added stock_unit column to products")
    
    # Extend orders table with new columns
    if not column_exists(conn, 'orders', 'status'):
        conn.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'pending'")
        print("✓ Added status column to orders")
    
    if not column_exists(conn, 'orders', 'special_instructions'):
        conn.execute("ALTER TABLE orders ADD COLUMN special_instructions TEXT")
        print("✓ Added special_instructions column to orders")
    
    if not column_exists(conn, 'orders', 'tag'):
        conn.execute("ALTER TABLE orders ADD COLUMN tag TEXT DEFAULT ''")
        print("✓ Added tag column to orders")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    run_migration()