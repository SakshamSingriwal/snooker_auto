from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from backend import database as db
from backend.models import CreateOrderRequest, StopSessionRequest
from typing import Optional, List

app = FastAPI(title="Snooker Cafe API", version="1.0.0")

# CORS middleware for mobile access from any local IP
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
    price: Optional[float] = Query(None)
):
    if price is not None and price < 0:
        raise HTTPException(400, "Price cannot be negative")
    db.update_product(product_id, name, price)
    return {"status": "ok"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    db.delete_product(product_id)
    return {"status": "ok"}

@app.post("/api/order")
def create_order(req: CreateOrderRequest):
    if not req.items:
        raise HTTPException(400, "Order must contain at least one item")
    items = [{"product_id": i.product_id, "quantity": i.quantity} for i in req.items]
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

@app.get("/order", response_class=HTMLResponse)
def order_page(table_id: int = 1):
    html_path = Path(__file__).parent.parent / "customer_frontend" / "order.html"
    if not html_path.exists():
        return HTMLResponse("<h1>order.html not found</h1>", status_code=404)
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("{{TABLE_ID}}", str(table_id))
    return HTMLResponse(content=html)