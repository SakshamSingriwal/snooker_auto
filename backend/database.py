import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "snooker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            min_minutes INTEGER DEFAULT 20,
            rate_per_minute REAL DEFAULT 2.0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            customer_name TEXT,
            total_bill REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY(table_id) REFERENCES tables(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            session_id INTEGER,
            customer_type TEXT,
            special_requests TEXT,
            order_time TEXT,
            total_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # Default settings
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin123')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cafe_name', 'Snooker Cafe')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('currency_symbol', '₹')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('default_min_minutes', '20')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('default_rate_per_minute', '2.0')")

    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

def get_tables():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tables").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_table(name, category, min_minutes, rate_per_minute):
    conn = get_conn()
    # Check for duplicate
    existing = conn.execute("SELECT id FROM tables WHERE name=?", (name,)).fetchone()
    if existing:
        conn.close()
        return None  # Duplicate
    conn.execute(
        "INSERT INTO tables (name, type, min_minutes, rate_per_minute) VALUES (?,?,?,?)",
        (name, category, min_minutes, rate_per_minute)
    )
    conn.commit()
    tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return tid

def update_table(table_id, min_minutes, rate_per_minute):
    conn = get_conn()
    conn.execute(
        "UPDATE tables SET min_minutes=?, rate_per_minute=? WHERE id=?",
        (min_minutes, rate_per_minute, table_id)
    )
    conn.commit()
    conn.close()

def get_active_sessions():
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.id, s.table_id, s.start_time, t.name as table_name
        FROM sessions s
        JOIN tables t ON t.id = s.table_id
        WHERE s.status = 'active'
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def start_session(table_id):
    conn = get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO sessions (table_id, start_time, status) VALUES (?,?,?)",
        (table_id, now, "active")
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid

def stop_session(session_id, customer_name):
    conn = get_conn()
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return {"error": "Session not found"}
    if session["status"] != "active":
        conn.close()
        return {"error": "Session already stopped"}

    table = conn.execute("SELECT * FROM tables WHERE id=?", (session["table_id"],)).fetchone()
    start = datetime.fromisoformat(session["start_time"])
    end = datetime.now()
    elapsed_minutes = max((end - start).total_seconds() / 60, table["min_minutes"])
    time_charge = elapsed_minutes * table["rate_per_minute"]

    # Sum up food/drink orders linked to this session
    food_total_row = conn.execute(
        "SELECT COALESCE(SUM(total_amount),0) as total FROM orders WHERE session_id=?",
        (session_id,)
    ).fetchone()
    food_total = food_total_row["total"] if food_total_row else 0

    total_bill = round(time_charge + food_total, 2)

    conn.execute(
        "UPDATE sessions SET end_time=?, customer_name=?, total_bill=?, status='closed' WHERE id=?",
        (end.isoformat(), customer_name, total_bill, session_id)
    )
    conn.commit()
    conn.close()
    return {
        "session_id": session_id,
        "customer_name": customer_name,
        "elapsed_minutes": round(elapsed_minutes, 1),
        "time_charge": round(time_charge, 2),
        "food_total": round(food_total, 2),
        "total_bill": total_bill
    }

def get_products():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM products WHERE active=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_product(name, category, price):
    if price < 0:
        return None
    conn = get_conn()
    conn.execute("INSERT INTO products (name, category, price) VALUES (?,?,?)", (name, category, price))
    conn.commit()
    conn.close()
    return True

def update_product(product_id, name=None, price=None, current_stock=None, min_stock_threshold=None):
    if price is not None and price < 0:
        return None
    conn = get_conn()
    if name:
        conn.execute("UPDATE products SET name=? WHERE id=?", (name, product_id))
    if price is not None:
        conn.execute("UPDATE products SET price=? WHERE id=?", (price, product_id))
    if current_stock is not None:
        conn.execute("UPDATE products SET current_stock=? WHERE id=?", (current_stock, product_id))
    if min_stock_threshold is not None:
        conn.execute("UPDATE products SET min_stock_threshold=? WHERE id=?", (min_stock_threshold, product_id))
    conn.commit()
    conn.close()
    return True

def delete_product(product_id):
    conn = get_conn()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def create_order(table_id, customer_type, items, special_requests=None):
    if not items:
        return None
    conn = get_conn()
    now = datetime.now().isoformat()

    # Find active session for this table (if any)
    session_row = conn.execute(
        "SELECT id FROM sessions WHERE table_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (table_id,)
    ).fetchone()
    session_id = session_row["id"] if session_row else None

    total = 0
    for item in items:
        product = conn.execute("SELECT price FROM products WHERE id=?", (item["product_id"],)).fetchone()
        if product:
            total += product["price"] * item["quantity"]

    cur = conn.execute(
        "INSERT INTO orders (table_id, session_id, customer_type, special_requests, order_time, total_amount, status) VALUES (?,?,?,?,?,?,?)",
        (table_id, session_id, customer_type, special_requests, now, round(total, 2), "pending")
    )
    order_id = cur.lastrowid

    for item in items:
        product = conn.execute("SELECT price FROM products WHERE id=?", (item["product_id"],)).fetchone()
        unit_price = product["price"] if product else 0
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
            (order_id, item["product_id"], item["quantity"], unit_price)
        )

    conn.commit()
    conn.close()
    return order_id

def get_order_items(order_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT oi.product_id, oi.quantity, oi.unit_price, p.name as product_name
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_orders():
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.id, o.table_id, o.customer_type, o.order_time, o.total_amount,
               t.name as table_name
        FROM orders o
        LEFT JOIN tables t ON t.id = o.table_id
        WHERE o.status = 'pending'
        ORDER BY o.order_time ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_orders_by_table(table_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.id, o.table_id, o.customer_type, o.order_time, o.total_amount, o.special_requests,
               t.name as table_name
        FROM orders o
        LEFT JOIN tables t ON t.id = o.table_id
        WHERE o.status = 'pending' AND o.table_id = ?
        ORDER BY o.order_time ASC
    """, (table_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def complete_order(order_id):
    conn = get_conn()
    conn.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

def update_order_status(order_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

def get_order_status(order_id: int) -> str:
    conn = get_conn()
    row = conn.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row["status"] if row else "unknown"

def update_order_items(order_id: int, items: List[Dict]):
    conn = get_conn()
    # Delete old items
    conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
    
    # Calculate total
    total = 0
    for item in items:
        product = conn.execute("SELECT price FROM products WHERE id=?", (item["product_id"],)).fetchone()
        if product:
            total += product["price"] * item["quantity"]
        
        # Insert new items
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, item["product_id"], item["quantity"], product["price"] if product else 0)
        )
    
    conn.execute("UPDATE orders SET total_amount=? WHERE id=?", (round(total, 2), order_id))
    conn.commit()
    conn.close()

def set_order_tag(order_id: int, tag: str):
    conn = get_conn()
    conn.execute("UPDATE orders SET tag=? WHERE id=?", (tag, order_id))
    conn.commit()
    conn.close()

def get_sales_summary():
    conn = get_conn()
    sessions = conn.execute("""
        SELECT DATE(end_time) as date, SUM(total_bill) as revenue, COUNT(*) as count
        FROM sessions WHERE status='closed'
        GROUP BY DATE(end_time)
        ORDER BY date DESC
        LIMIT 30
    """).fetchall()
    orders = conn.execute("""
        SELECT DATE(order_time) as date, SUM(total_amount) as revenue, COUNT(*) as count
        FROM orders WHERE status='completed'
        GROUP BY DATE(order_time)
        ORDER BY date DESC
        LIMIT 30
    """).fetchall()
    conn.close()
    return {
        "sessions": [dict(r) for r in sessions],
        "orders": [dict(r) for r in orders]
    }

def get_top_selling_items():
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as total_qty, SUM(oi.quantity * oi.unit_price) as revenue
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        JOIN orders o ON o.id = oi.order_id
        WHERE o.status = 'completed'
        GROUP BY p.id, p.name
        ORDER BY total_qty DESC
        LIMIT 10
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_sales_by_date(start_date=None, end_date=None):
    conn = get_conn()
    sessions_query = """
        SELECT DATE(end_time) as date, SUM(total_bill) as revenue, COUNT(*) as count
        FROM sessions WHERE status='closed'
    """
    orders_query = """
        SELECT DATE(order_time) as date, SUM(total_amount) as revenue, COUNT(*) as count
        FROM orders WHERE status='completed'
    """
    params = []
    if start_date:
        sessions_query += " AND date(end_time) >= ?"
        orders_query += " AND date(order_time) >= ?"
        params.append(start_date)
    if end_date:
        sessions_query += " AND date(end_time) <= ?"
        orders_query += " AND date(order_time) <= ?"
        params.append(end_date)
    sessions_query += " GROUP BY date ORDER BY date"
    orders_query += " GROUP BY date ORDER BY date"
    
    sessions = conn.execute(sessions_query, params).fetchall()
    orders = conn.execute(orders_query, params).fetchall()
    conn.close()
    return {
        "sessions": [dict(r) for r in sessions],
        "orders": [dict(r) for r in orders]
    }

def archive_month(year, month):
    import shutil
    archive_path = Path(__file__).parent.parent / "data" / f"archive_{year}_{month:02d}.db"
    shutil.copy(DB_PATH, archive_path)
    conn = get_conn()
    conn.execute(
        "DELETE FROM sessions WHERE status='closed' AND strftime('%Y', end_time)=? AND strftime('%m', end_time)=?",
        (str(year), f"{month:02d}")
    )
    conn.execute(
        "DELETE FROM orders WHERE status='completed' AND strftime('%Y', order_time)=? AND strftime('%m', order_time)=?",
        (str(year), f"{month:02d}")
    )
    conn.commit()
    conn.close()
    return archive_path