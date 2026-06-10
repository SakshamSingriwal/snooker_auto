from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sqlite3
from backend import database as db
from backend import inventory
from backend import combos
from backend.models import CreateOrderRequest, StopSessionRequest
from typing import Optional, List, Dict

app = FastAPI(title="Snooker Cafe API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent.parent / "customer_frontend"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def startup():
    db.init_db()

# ── TABLES ──────────────────────────────────────────────────────────────

@app.get("/api/tables")
def get_tables():
    return db.get_tables()

@app.post("/api/tables")
def add_table(
    name: str = Query(...),
    category: str = Query(...),
    min_minutes: int = Query(20),
    rate_per_minute: float = Query(2.0)
):
    if rate_per_minute <= 0:
        raise HTTPException(400, "Rate per minute must be greater than 0")
    tid = db.add_table(name, category, min_minutes, rate_per_minute)
    if tid is None:
        raise HTTPException(400, f"Table name '{name}' already exists")
    return {"status": "ok", "table_id": tid}

@app.put("/api/tables/{table_id}")
def update_table(
    table_id: int,
    min_minutes: int = Query(...),
    rate_per_minute: float = Query(...)
):
    if rate_per_minute <= 0:
        raise HTTPException(400, "Rate per minute must be greater than 0")
    db.update_table(table_id, min_minutes, rate_per_minute)
    return {"status": "ok"}

# ── SESSIONS ───────────────────────────────────────────────────────────

@app.get("/api/active_sessions")
def get_active_sessions():
    return db.get_active_sessions()

@app.post("/api/start_session/{table_id}")
def start_session(table_id: int):
    session_id = db.start_session(table_id)
    return {"session_id": session_id}

@app.post("/api/stop_session/{session_id}")
def stop_session(session_id: int, req: StopSessionRequest):
    result = db.stop_session(session_id, req.customer_name)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

# ── PRODUCTS ───────────────────────────────────────────────────────────

@app.get("/api/products")
def get_products():
    return db.get_products()

@app.post("/api/products")
def add_product(
    name: str = Query(...),
    category: str = Query(...),
    price: float = Query(...)
):
    if price < 0:
        raise HTTPException(400, "Price cannot be negative")
    db.add_product(name, category, price)
    return {"status": "ok"}

@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    name: Optional[str] = Query(None),
    price: Optional[float] = Query(None),
    current_stock: Optional[float] = Query(None),
    min_stock_threshold: Optional[float] = Query(None)
):
    if price is not None and price < 0:
        raise HTTPException(400, "Price cannot be negative")
    db.update_product(product_id, name, price, current_stock, min_stock_threshold)
    return {"status": "ok"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    db.delete_product(product_id)
    return {"status": "ok"}

# ── INVENTORY ────────────────────────────────────────────────────────────

@app.get("/api/inventory")
def get_inventory():
    return inventory.get_ingredients()

@app.get("/api/inventory/low_stock")
def get_low_stock():
    return {"ingredients": inventory.get_low_stock_ingredients()}

@app.post("/api/inventory/ingredient")
def add_ingredient(
    name: str = Query(...),
    unit: str = Query("pcs"),
    min_threshold: float = Query(10),
    vendor_id: Optional[int] = Query(None)
):
    iid = inventory.add_ingredient(name, unit, min_threshold, vendor_id)
    return {"ingredient_id": iid}

@app.put("/api/inventory/ingredient/{ingredient_id}")
def update_ingredient(
    ingredient_id: int,
    name: Optional[str] = Query(None),
    unit: Optional[str] = Query(None),
    min_threshold: Optional[float] = Query(None),
    vendor_id: Optional[int] = Query(None),
    current_stock: Optional[float] = Query(None)
):
    inventory.update_ingredient(ingredient_id, name, unit, min_threshold, vendor_id, current_stock)
    return {"status": "ok"}

# ── RECIPES ──────────────────────────────────────────────────────────────

@app.get("/api/recipes")
def get_recipes():
    return inventory.get_recipes()

@app.get("/api/recipes/product/{product_id}")
def get_product_recipe(product_id: int):
    return {"recipe": inventory.get_recipe_for_product(product_id)}

@app.post("/api/recipes/product/{product_id}")
def set_product_recipe(product_id: int, ingredient_quantities: str = Query(...)):
    """ingredient_quantities format: "id1:qty1,id2:qty2" """
    pairs = []
    for pair in ingredient_quantities.split(","):
        if ":" in pair:
            iid, qty = pair.split(":")
            pairs.append((int(iid), float(qty)))
    inventory.set_recipe(product_id, pairs)
    return {"status": "ok"}

# ── VENDORS ──────────────────────────────────────────────────────────────

@app.get("/api/vendors")
def get_vendors():
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM vendors").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/vendors")
def add_vendor(
    name: str = Query(...),
    contact: Optional[str] = Query(None),
    lead_time_days: int = Query(1)
):
    conn = sqlite3.connect(db.DB_PATH)
    cur = conn.execute(
        "INSERT INTO vendors (name, contact, lead_time_days) VALUES (?, ?, ?)",
        (name, contact, lead_time_days)
    )
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return {"vendor_id": vid}

@app.put("/api/vendors/{vendor_id}")
def update_vendor(
    vendor_id: int,
    name: Optional[str] = Query(None),
    contact: Optional[str] = Query(None),
    lead_time_days: Optional[int] = Query(None)
):
    conn = sqlite3.connect(db.DB_PATH)
    if name:
        conn.execute("UPDATE vendors SET name=? WHERE id=?", (name, vendor_id))
    if contact:
        conn.execute("UPDATE vendors SET contact=? WHERE id=?", (contact, vendor_id))
    if lead_time_days is not None:
        conn.execute("UPDATE vendors SET lead_time_days=? WHERE id=?", (lead_time_days, vendor_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── COMBOS ────────────────────────────────────────────────────────────────

@app.get("/api/combos")
def get_combos(active_only: bool = False):
    return combos.get_combos(active_only)

@app.get("/api/combos/active")
def get_active_combos():
    import datetime
    hour = datetime.datetime.now().hour
    time_of_day = None
    if 12 <= hour < 16:
        time_of_day = "lunch"
    elif 16 <= hour < 19:
        time_of_day = "evening"
    
    active_combos = combos.get_combos(active_only=True)
    return active_combos

@app.post("/api/combos")
def create_combo(
    name: str = Query(...),
    discount_amount: float = Query(0),
    time_of_day: Optional[str] = Query(None),
    description: str = Query("")
):
    cid = combos.add_combo(name, None, discount_amount, time_of_day, description)
    return {"combo_id": cid}

@app.post("/api/combos/{combo_id}/items")
def add_combo_item_endpoint(combo_id: int, product_id: int = Query(...), quantity: int = Query(1)):
    combos.add_combo_item(combo_id, product_id, quantity)
    return {"status": "ok"}

@app.post("/api/combos/{combo_id}/activate")
def activate_combo_endpoint(combo_id: int):
    combos.activate_combo(combo_id, True)
    return {"status": "ok"}

@app.post("/api/combos/generate_smart")
def generate_smart_combos():
    suggestions = combos.generate_smart_combos()
    return {"suggestions": suggestions}

@app.post("/api/combos/suggestion/{product_1_id}/{product_2_id}")
def create_suggestion_combo(product_1_id: int, product_2_id: int, name: str = Query(...)):
    cid = combos.create_suggested_combo(product_1_id, product_2_id, name)
    return {"combo_id": cid}

@app.delete("/api/combos/{combo_id}")
def delete_combo_endpoint(combo_id: int):
    combos.delete_combo(combo_id)
    return {"status": "ok"}

@app.get("/api/suggestions/{product_id}")
def get_suggestions_endpoint(product_id: int):
    return {"suggestions": combos.get_suggestions(product_id)}

# ── ORDERS ────────────────────────────────────────────────────────────────

@app.post("/api/order")
def create_order(req: CreateOrderRequest):
    if not req.items:
        raise HTTPException(400, "Order must contain at least one item")
    
    items = [{"product_id": i.product_id, "quantity": i.quantity} for i in req.items]
    
    # Check and deduct ingredients atomically
    success, error = inventory.deduct_ingredients_for_order(items)
    if not success:
        raise HTTPException(400, f"Insufficient ingredients: {error}")
    
    order_id = db.create_order(req.table_id, req.customer_type, items, req.special_requests)
    return {"order_id": order_id}

@app.get("/api/order/{order_id}/items")
def get_order_items_endpoint(order_id: int):
    items = db.get_order_items(order_id)
    return items

@app.get("/api/pending_orders")
def get_pending_orders(table_id: Optional[int] = None):
    if table_id:
        return db.get_pending_orders_by_table(table_id)
    return db.get_pending_orders()

@app.post("/api/order/{order_id}/complete")
def complete_order(order_id: int):
    db.complete_order(order_id)
    return {"status": "completed"}

@app.put("/api/order/{order_id}/status")
def update_order_status(order_id: int, status: str = Query(...)):
    """Update order status: pending, preparing, ready, completed"""
    db.update_order_status(order_id, status)
    return {"status": "updated"}

@app.get("/api/order/{order_id}/status")
def get_order_status(order_id: int):
    status = db.get_order_status(order_id)
    return {"order_id": order_id, "status": status}

@app.put("/api/order/{order_id}/edit")
def edit_order(order_id: int, items: str = Query(...)):
    """Edit order items. Format: "id1:qty1,id2:qty2" - replaces all items"""
    # Get existing items first
    old_items = db.get_order_items(order_id)
    
    # Add back old ingredients
    inventory.add_ingredients_back_for_items([
        {"product_id": i["product_id"], "quantity": i["quantity"]} for i in old_items
    ])
    
    # Parse and validate new items
    new_items = []
    for pair in items.split(","):
        if ":" in pair:
            pid, qty = pair.split(":")
            new_items.append({"product_id": int(pid), "quantity": int(qty)})
    
    # Check new ingredients availability
    success, error = inventory.deduct_ingredients_for_order(new_items)
    if not success:
        raise HTTPException(400, f"Insufficient ingredients: {error}")
    
    # Update order and items
    db.update_order_items(order_id, new_items)
    return {"status": "updated"}

@app.put("/api/order/{order_id}/tag")
def set_order_tag(order_id: int, tag: str = Query(...)):
    db.set_order_tag(order_id, tag)
    return {"status": "ok"}

# ── SALES & SETTINGS ─────────────────────────────────────────────────────

@app.get("/api/sales_summary")
def sales_summary(start_date: Optional[str] = None, end_date: Optional[str] = None):
    if start_date or end_date:
        return db.get_sales_by_date(start_date, end_date)
    return db.get_sales_summary()

@app.get("/api/top_selling")
def get_top_selling():
    return db.get_top_selling_items()

@app.get("/api/settings")
def get_settings():
    return {
        "cafe_name": db.get_setting("cafe_name", "Snooker Cafe"),
        "currency_symbol": db.get_setting("currency_symbol", "₹"),
        "default_min_minutes": int(db.get_setting("default_min_minutes", "20")),
        "default_rate_per_minute": float(db.get_setting("default_rate_per_minute", "2.0"))
    }

@app.post("/api/settings")
def update_settings(
    cafe_name: Optional[str] = Query(None),
    currency_symbol: Optional[str] = Query(None),
    default_min_minutes: Optional[int] = Query(None),
    default_rate_per_minute: Optional[float] = Query(None)
):
    if cafe_name:
        db.set_setting("cafe_name", cafe_name)
    if currency_symbol:
        db.set_setting("currency_symbol", currency_symbol)
    if default_min_minutes is not None:
        db.set_setting("default_min_minutes", str(default_min_minutes))
    if default_rate_per_minute is not None:
        if default_rate_per_minute <= 0:
            raise HTTPException(400, "Default rate must be greater than 0")
        db.set_setting("default_rate_per_minute", str(default_rate_per_minute))
    return {"status": "ok"}

@app.get("/api/change_password")
def change_password(current: str = Query(...), new: str = Query(...)):
    current_pass = db.get_setting("admin_password", "admin123")
    if current != current_pass:
        raise HTTPException(400, "Current password is incorrect")
    db.set_setting("admin_password", new)
    return {"status": "ok"}

# ── ORDER PAGE ────────────────────────────────────────────────────────────

@app.get("/order", response_class=HTMLResponse)
def order_page(table_id: int = 1):
    html_path = Path(__file__).parent.parent / "customer_frontend" / "order.html"
    if not html_path.exists():
        return HTMLResponse("<h1>order.html not found</h1>", status_code=404)
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("{{TABLE_ID}}", str(table_id))
    return HTMLResponse(content=html)