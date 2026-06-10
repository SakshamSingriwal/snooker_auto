"""
Combo management and smart suggestion engine for snooker_auto.
"""
from pathlib import Path
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "snooker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ── COMBOS ────────────────────────────────────────────────────────────────

def get_combos(active_only: bool = False) -> List[Dict]:
    """Get all combos or only active ones."""
    conn = get_conn()
    query = "SELECT * FROM combos"
    if active_only:
        query += " WHERE is_active=1"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_combo(combo_id: int) -> Optional[Dict]:
    """Get single combo with items."""
    conn = get_conn()
    combo = conn.execute("SELECT * FROM combos WHERE id=?", (combo_id,)).fetchone()
    if not combo:
        conn.close()
        return None
    
    items = conn.execute("""
        SELECT ci.*, p.name as product_name, p.price 
        FROM combo_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.combo_id = ?
    """, (combo_id,)).fetchall()
    
    conn.close()
    result = dict(combo)
    result["items"] = [dict(r) for r in items]
    return result

def add_combo(name: str, price: Optional[float] = None, discount: float = 0, 
              time_of_day: Optional[str] = None, description: str = "") -> int:
    """Create a new combo."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO combos (name, price, discount_amount, time_of_day, description) VALUES (?, ?, ?, ?, ?)",
        (name, price, discount, time_of_day, description)
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid

def add_combo_item(combo_id: int, product_id: int, quantity: int = 1):
    """Add item to combo."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO combo_items (combo_id, product_id, quantity) VALUES (?, ?, ?)",
        (combo_id, product_id, quantity)
    )
    conn.commit()
    conn.close()

def calculate_combo_price(combo_id: int) -> float:
    """Calculate combo price from items (sum - discount)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT SUM(p.price * ci.quantity) as total
        FROM combo_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.combo_id = ?
    """, (combo_id,)).fetchone()
    conn.close()
    return rows["total"] if rows and rows["total"] else 0

def activate_combo(combo_id: int, is_active: bool = True):
    """Activate or deactivate a combo."""
    conn = get_conn()
    conn.execute("UPDATE combos SET is_active=?, is_suggested=0 WHERE id=?", (int(is_active), combo_id))
    conn.commit()
    conn.close()

def delete_combo(combo_id: int):
    """Delete a combo and its items."""
    conn = get_conn()
    conn.execute("DELETE FROM combo_items WHERE combo_id=?", (combo_id,))
    conn.execute("DELETE FROM combos WHERE id=?", (combo_id,))
    conn.commit()
    conn.close()

# ── SMART COMBO GENERATION ────────────────────────────────────────────────

def get_recent_orders(days: int = 7) -> List[Dict]:
    """Get completed orders from last N days."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT oi.product_id, p.name as product_name
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.status = 'completed' 
        AND o.order_time >= datetime('now', f'-{days} days')
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def generate_smart_combos(min_cooccurrence: int = 3) -> List[Dict]:
    """Analyze order history and suggest combos."""
    orders = get_recent_orders(7)
    
    # Group products by order (simplified: just count co-occurrences)
    product_pairs = {}
    product_counts = {}
    
    # Get unique orders
    conn = get_conn()
    order_ids = conn.execute("""
        SELECT DISTINCT o.id FROM orders o 
        WHERE o.status = 'completed' AND o.order_time >= datetime('now', '-7 days')
    """).fetchall()
    
    for oid in order_ids:
        items = conn.execute("""
            SELECT product_id FROM order_items WHERE order_id = ?
        """, (oid[0],)).fetchall()
        product_ids = [i[0] for i in items]
        
        # Count individual products
        for pid in product_ids:
            product_counts[pid] = product_counts.get(pid, 0) + 1
        
        # Count pairs
        for i in range(len(product_ids)):
            for j in range(i + 1, len(product_ids)):
                pair = tuple(sorted([product_ids[i], product_ids[j]]))
                product_pairs[pair] = product_pairs.get(pair, 0) + 1
    
    conn.close()
    
    # Find pairs that meet threshold and aren't already combos
    suggestions = []
    for pair, count in product_pairs.items():
        if count >= min_cooccurrence:
            # Check if this pair is already in an active combo
            conn = get_conn()
            existing = conn.execute("""
                SELECT c.id FROM combos c
                JOIN combo_items ci1 ON ci1.combo_id = c.id
                JOIN combo_items ci2 ON ci2.combo_id = c.id
                WHERE c.is_active = 1 
                AND ci1.product_id = ? AND ci2.product_id = ?
            """, (pair[0], pair[1])).fetchone()
            conn.close()
            
            if not existing:
                # Get product names
                conn = get_conn()
                p1 = conn.execute("SELECT name FROM products WHERE id=?", (pair[0],)).fetchone()
                p2 = conn.execute("SELECT name FROM products WHERE id=?", (pair[1],)).fetchone()
                conn.close()
                
                if p1 and p2:
                    suggestions.append({
                        "product_1_id": pair[0],
                        "product_1_name": p1[0],
                        "product_2_id": pair[1],
                        "product_2_name": p2[0],
                        "cooccurrence_count": count
                    })
    
    return sorted(suggestions, key=lambda x: -x["cooccurrence_count"])[:10]

def create_suggested_combo(product_1_id: int, product_2_id: int, name: str) -> int:
    """Create a suggested combo from two products."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO combos (name, is_suggested, is_active) VALUES (?, 1, 0)",
        (name,)
    )
    combo_id = cur.lastrowid
    conn.execute("INSERT INTO combo_items (combo_id, product_id, quantity) VALUES (?, ?, 1)",
                 (combo_id, product_1_id))
    conn.execute("INSERT INTO combo_items (combo_id, product_id, quantity) VALUES (?, ?, 1)",
                 (combo_id, product_2_id))
    conn.commit()
    conn.close()
    return combo_id

# ── SUGGESTIONS ENDPOINT ────────────────────────────────────────────────────

def get_suggestions(product_id: int, time_of_day: Optional[str] = None) -> List[Dict]:
    """Get combo/add-on suggestions for a product."""
    conn = get_conn()
    
    # Get time-based active combos
    query = """
        SELECT c.*, ci.product_id as item_product_id, p.name as item_name
        FROM combos c
        JOIN combo_items ci ON ci.combo_id = c.id
        JOIN products p ON p.id = ci.product_id
        WHERE c.is_active = 1
    """
    params = []
    
    if time_of_day:
        query += " AND (c.time_of_day IS NULL OR c.time_of_day = ?)"
        params.append(time_of_day)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    # Filter combos that contain the product
    suggestions = []
    seen_combos = set()
    for row in rows:
        if row["id"] not in seen_combos:
            suggestions.append(dict(row))
            seen_combos.add(row["id"])
    
    return suggestions[:2]  # Max 2 suggestions