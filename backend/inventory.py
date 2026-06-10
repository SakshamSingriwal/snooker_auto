"""
Inventory and recipe management module for snooker_auto.
"""
from pathlib import Path
import sqlite3
from typing import List, Optional, Dict, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "snooker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ── INGREDIENTS ────────────────────────────────────────────────────────────────

def get_ingredients() -> List[Dict]:
    """Get all ingredients with current stock levels."""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT i.*, v.name as vendor_name 
            FROM ingredients i 
            LEFT JOIN vendors v ON v.id = i.vendor_id
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_ingredient(ingredient_id: int) -> Optional[Dict]:
    """Get single ingredient by ID."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM ingredients WHERE id=?", (ingredient_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def add_ingredient(name: str, unit: str = "pcs", min_threshold: float = 10, vendor_id: Optional[int] = None) -> int:
    """Add a new ingredient."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO ingredients (name, unit, min_threshold, vendor_id) VALUES (?, ?, ?, ?)",
        (name, unit, min_threshold, vendor_id)
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid

def update_ingredient(ingredient_id: int, name: Optional[str] = None, unit: Optional[str] = None, 
                      min_threshold: Optional[float] = None, vendor_id: Optional[int] = None,
                      current_stock: Optional[float] = None) -> bool:
    """Update ingredient details."""
    conn = get_conn()
    if name:
        conn.execute("UPDATE ingredients SET name=? WHERE id=?", (name, ingredient_id))
    if unit:
        conn.execute("UPDATE ingredients SET unit=? WHERE id=?", (unit, ingredient_id))
    if min_threshold is not None:
        conn.execute("UPDATE ingredients SET min_threshold=? WHERE id=?", (min_threshold, ingredient_id))
    if vendor_id is not None:
        conn.execute("UPDATE ingredients SET vendor_id=? WHERE id=?", (vendor_id, ingredient_id))
    if current_stock is not None:
        conn.execute("UPDATE ingredients SET current_stock=? WHERE id=?", (current_stock, ingredient_id))
    conn.commit()
    conn.close()
    return True

def get_low_stock_ingredients() -> List[Dict]:
    """Get ingredients below threshold."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM ingredients 
        WHERE current_stock < min_threshold
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── RECIPE MANAGEMENT ───────────────────────────────────────────────────────────

def get_recipes() -> List[Dict]:
    """Get all product recipes."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT ri.product_id, p.name as product_name, ri.ingredient_id, i.name as ingredient_name,
               ri.quantity, i.unit, i.current_stock
        FROM recipe_ingredients ri
        JOIN products p ON p.id = ri.product_id
        JOIN ingredients i ON i.id = ri.ingredient_id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recipe_for_product(product_id: int, conn=None) -> List[Dict]:
    """Get recipe (ingredients) for a specific product."""
    if conn is None:
        conn = get_conn()
        rows = conn.execute("""
            SELECT ri.*, i.name as ingredient_name, i.current_stock, i.min_threshold, i.unit
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.product_id = ?
        """, (product_id,)).fetchall()
        conn.close()
    else:
        rows = conn.execute("""
            SELECT ri.*, i.name as ingredient_name, i.current_stock, i.min_threshold, i.unit
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.product_id = ?
        """, (product_id,)).fetchall()
    return [dict(r) for r in rows]

def set_recipe(product_id: int, ingredient_quantities: List[Tuple[int, float]]):
    """Set recipe for a product. ingredient_quantities = [(ingredient_id, quantity), ...]"""
    conn = get_conn()
    conn.execute("DELETE FROM recipe_ingredients WHERE product_id=?", (product_id,))
    for ingredient_id, quantity in ingredient_quantities:
        conn.execute(
            "INSERT INTO recipe_ingredients (product_id, ingredient_id, quantity) VALUES (?, ?, ?)",
            (product_id, ingredient_id, quantity)
        )
    conn.commit()
    conn.close()

def check_ingredients_available(product_id: int, quantity: int, conn=None) -> Tuple[bool, Optional[str]]:
    """Check if enough ingredients are available for a product order.
    Returns (is_available, missing_ingredient_name)"""
    should_close = False
    if conn is None:
        conn = get_conn()
        should_close = True
    try:
        recipe = get_recipe_for_product(product_id, conn)
        for item in recipe:
            required = item["quantity"] * quantity
            if conn.execute("SELECT current_stock FROM ingredients WHERE id=?", (item["ingredient_id"],)).fetchone()[0] < required:
                return False, f"{item['ingredient_name']} (insufficient stock)"
        return True, None
    finally:
        if should_close:
            conn.close()

def deduct_ingredients_for_order(items: List[Dict]) -> Tuple[bool, Optional[str]]:
    """Deduct ingredients for all items in an order.
    Returns (success, error_message). Uses transaction for atomicity."""
    conn = get_conn()
    try:
        # First, verify all ingredients are available
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            available, missing = check_ingredients_available(product_id, quantity, conn)
            if not available:
                return False, f"Insufficient stock: {missing}"
        
        # Deduct ingredients
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            recipe = get_recipe_for_product(product_id, conn)
            for ri in recipe:
                new_stock = ri["current_stock"] - (ri["quantity"] * quantity)
                conn.execute(
                    "UPDATE ingredients SET current_stock=? WHERE id=?",
                    (new_stock, ri["ingredient_id"])
                )
        
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def add_ingredients_back_for_items(items: List[Dict]):
    """Add ingredients back when order is edited (items removed)."""
    conn = get_conn()
    try:
        for item in items:
            recipe = get_recipe_for_product(item["product_id"], conn)
            for ri in recipe:
                conn.execute(
                    "UPDATE ingredients SET current_stock = current_stock + ? WHERE id=?",
                    (ri["quantity"] * item["quantity"], ri["ingredient_id"])
                )
        conn.commit()
    finally:
        conn.close()