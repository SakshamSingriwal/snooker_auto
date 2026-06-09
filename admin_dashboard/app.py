import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from backend.auth import check_password

st.set_page_config(page_title="Snooker Manager", layout="wide")

if not check_password():
    st.stop()

API_BASE = "http://localhost:8000"

st.title("🎱 Snooker Cafe Manager")
st.caption("Simple. Fast. Works offline.")

# API Status indicator
def check_api_status():
    try:
        requests.get(f"{API_BASE}/api/tables", timeout=2)
        return True
    except:
        return False

st.session_state.menu = st.sidebar.radio("Menu", ["Live", "Tables & Rates", "Menu Items", "Orders", "Reports", "Settings"])

# Auto-refresh every 15 seconds on Live page
if st.session_state.menu == "Live":
    st_autorefresh(interval=15000, key="live_refresh")

# API Status in sidebar
api_ok = check_api_status()
if api_ok:
    st.sidebar.success("🟢 API Connected")
else:
    st.sidebar.error("🔴 API Offline")

def get_tables():
    try:
        resp = requests.get(f"{API_BASE}/api/tables", timeout=5)
        return resp.json() if resp.ok else []
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def get_active():
    try:
        resp = requests.get(f"{API_BASE}/api/active_sessions", timeout=5)
        return resp.json() if resp.ok else []
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def get_pending():
    try:
        resp = requests.get(f"{API_BASE}/api/pending_orders", timeout=5)
        return resp.json() if resp.ok else []
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def get_products():
    try:
        resp = requests.get(f"{API_BASE}/api/products", timeout=5)
        return resp.json() if resp.ok else []
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def get_sales_summary():
    try:
        resp = requests.get(f"{API_BASE}/api/sales_summary", timeout=5)
        return resp.json() if resp.ok else {"sessions": [], "orders": []}
    except Exception as e:
        st.error(f"API Error: {e}")
        return {"sessions": [], "orders": []}

def get_settings():
    try:
        resp = requests.get(f"{API_BASE}/api/settings", timeout=5)
        return resp.json() if resp.ok else {}
    except:
        return {}

def get_order_items(order_id):
    try:
        resp = requests.get(f"{API_BASE}/api/order/{order_id}/items", timeout=5)
        return resp.json() if resp.ok else []
    except:
        return []

def get_table_orders(table_id):
    try:
        resp = requests.get(f"{API_BASE}/api/pending_orders", params={"table_id": table_id}, timeout=5)
        return resp.json() if resp.ok else []
    except:
        return []

def get_top_selling():
    try:
        resp = requests.get(f"{API_BASE}/api/top_selling", timeout=5)
        return resp.json() if resp.ok else []
    except:
        return []

# Type icons
TYPE_ICONS = {
    "snooker": "🎱",
    "pool": "🎳",
    "ludo": "🎲",
    "carrom": "🪀",
    "chess": "♟️",
    "seating": "🪑"
}

CAT_COLORS = {
    "food": "#ff7f0e",
    "drink": "#1a5276",
    "hookah": "#8E44AD"
}

# ── LIVE ──────────────────────────────────────────────────────────────────────
if st.session_state.menu == "Live":
    st.header("🔥 Active Tables")
    active = get_active()
    if not active:
        st.info("No active sessions")
    else:
        for s in active:
            with st.container():
                st.markdown(f"""
                    <div style="background:#2d6a4f; border-radius:10px; padding:15px; margin:10px 0; border: 2px solid #1a4a2e;">
                        <div style="color:#f0ede8; font-weight:bold; font-size:18px;">{s['table_name']}</div>
                        <div style="color:#f0ede8; font-size:14px;">Started: {s['start_time'][:19]}</div>
                        <div style="color:#f4d03f; font-weight:bold; margin-top:5px;">{int((datetime.now() - datetime.fromisoformat(s['start_time'])).total_seconds() / 60)} min elapsed</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # View Orders expander
                with st.expander(f"📋 View Orders for {s['table_name']}", expanded=False):
                    orders = get_table_orders(s['table_id'])
                    if orders:
                        for o in orders:
                            st.write(f"Order #{o['id']} ({o['order_time'][:19]}) - ₹{o['total_amount']:.2f}")
                            if o.get('special_requests'):
                                st.caption(f"Note: {o['special_requests']}")
                            items = get_order_items(o['id'])
                            for item in items:
                                st.write(f"  - {item['quantity']} x {item['product_name']} @ ₹{item['unit_price']}")
                    else:
                        st.caption("No pending food orders")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if f"stop_name_{s['id']}" not in st.session_state:
                        st.session_state[f"stop_name_{s['id']}"] = ""
                    st.session_state[f"stop_name_{s['id']}"] = st.text_input(
                        "Customer name", key=f"name_input_{s['id']}"
                    )
                with col2:
                    if st.button("🔴 Stop", key=f"stop_{s['id']}", type="primary", disabled=not st.session_state.get(f"stop_name_{s['id']}")):
                        name = st.session_state.get(f"stop_name_{s['id']}", "")
                        if name:
                            try:
                                resp = requests.post(
                                    f"{API_BASE}/api/stop_session/{s['id']}",
                                    json={"customer_name": name},
                                    timeout=5
                                )
                                if resp.ok:
                                    bill = resp.json()
                                    st.success(f"✅ Bill: ₹{bill['total_bill']:.2f} | Time: {bill['elapsed_minutes']} min | Food: ₹{bill['food_total']:.2f}")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {resp.text}")
                            except Exception as e:
                                st.error(f"Error: {e}")

    st.divider()
    st.header("⏸️ Inactive Tables")
    tables = get_tables()
    active_ids = [s['table_id'] for s in active]
    cols = st.columns(4)
    for i, t in enumerate([t for t in tables if t['type'] != 'seating' and t['id'] not in active_ids]):
        icon = TYPE_ICONS.get(t['type'], "🎱")
        with cols[i % 4]:
            if st.button(f"{icon} {t['name']}", key=f"start_{t['id']}", type="secondary"):
                try:
                    requests.post(f"{API_BASE}/api/start_session/{t['id']}", timeout=5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ── TABLES & RATES ────────────────────────────────────────────────────────────
elif st.session_state.menu == "Tables & Rates":
    st.header("Manage Tables")
    tables = get_tables()
    if tables:
        df = pd.DataFrame(tables)
        st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Add New Table")
    type_map = {
        "Snooker": "snooker",
        "Pool": "pool",
        "Ludo": "ludo",
        "Carrom": "carrom",
        "Chess": "chess",
        "Seating": "seating"
    }
    settings = get_settings()
    c1, c2, c3, c4 = st.columns(4)
    selected_type = c1.selectbox("Type", list(type_map.keys()))
    name = c2.text_input("Table name", value=f"{selected_type} 1")
    min_min = c3.number_input("Min minutes", value=int(settings.get("default_min_minutes", 20)), step=5)
    rate = c4.number_input("Rate/min (₹)", value=float(settings.get("default_rate_per_minute", 2.0)), step=0.5)
    if st.button("Add Table"):
        if not name.strip():
            st.error("Table name cannot be empty")
        else:
            try:
                r = requests.post(f"{API_BASE}/api/tables", params={
                    "name": name, "category": type_map[selected_type],
                    "min_minutes": min_min, "rate_per_minute": rate
                }, timeout=5)
                if r.ok:
                    st.success("Table added")
                    st.rerun()
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("Edit Existing Table")
    for t in tables:
        if t['type'] != 'seating':
            icon = TYPE_ICONS.get(t['type'], "🎱")
            with st.expander(f"{icon} {t['name']} — ₹{t['rate_per_minute']}/min"):
                cc1, cc2, cc3 = st.columns([2, 2, 1])
                new_min = cc1.number_input("Min minutes", value=t['min_minutes'], key=f"min_{t['id']}")
                new_rate = cc2.number_input("Rate/min", value=float(t['rate_per_minute']), step=0.5, key=f"rate_{t['id']}")
                if cc3.button("Save", key=f"save_{t['id']}"):
                    try:
                        requests.put(f"{API_BASE}/api/tables/{t['id']}", params={"min_minutes": new_min, "rate_per_minute": new_rate}, timeout=5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                if cc2.button("📋 Duplicate", key=f"dup_{t['id']}"):
                    try:
                        dup_name = f"{t['name']} (Copy)"
                        requests.post(f"{API_BASE}/api/tables", params={
                            "name": dup_name, "category": t['type'],
                            "min_minutes": t['min_minutes'], "rate_per_minute": t['rate_per_minute']
                        }, timeout=5)
                        st.success(f"Duplicated as {dup_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ── MENU ITEMS ────────────────────────────────────────────────────────────────
elif st.session_state.menu == "Menu Items":
    st.header("Food & Drinks Menu")
    products = get_products()
    if products:
        df = pd.DataFrame(products)
        st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Add New Item")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Name")
    cat = c2.selectbox("Category", ["food", "drink", "hookah"])
    price = c3.number_input("Price (₹)", min_value=0.0, step=10.0)
    if st.button("Add Item"):
        if not name.strip():
            st.error("Item name cannot be empty")
        else:
            try:
                requests.post(f"{API_BASE}/api/products", params={"name": name, "category": cat, "price": price}, timeout=5)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("Edit / Delete Item")
    for p in products:
        cat_color = CAT_COLORS.get(p['category'], '#2d6a4f')
        with st.expander(f"{p['name']} — ₹{p['price']}"):
            cc1, cc2, cc3, cc4 = st.columns([3, 2, 1, 1])
            new_name = cc1.text_input("Name", value=p['name'], key=f"pname_{p['id']}")
            new_price = cc2.number_input("Price", value=float(p['price']), key=f"pprice_{p['id']}")
            if cc3.button("Update", key=f"upd_{p['id']}"):
                try:
                    requests.put(f"{API_BASE}/api/products/{p['id']}", params={"name": new_name, "price": new_price}, timeout=5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            if cc4.button("🗑️", key=f"del_{p['id']}"):
                try:
                    requests.delete(f"{API_BASE}/api/products/{p['id']}", timeout=5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ── ORDERS ────────────────────────────────────────────────────────────────────
elif st.session_state.menu == "Orders":
    st.header("Pending Orders")
    
    # Sound notification for new orders
    orders = get_pending()
    if st.session_state.get("_prev_order_count", 0) and len(orders) > st.session_state["_prev_order_count"]:
        st.components.v1.html("""
            <audio autoplay><source src="data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAA=" type="audio/wav"></audio>
        """, height=0)
    st.session_state["_prev_order_count"] = len(orders)
    
    if not orders:
        st.info("No pending orders")
    else:
        for o in orders:
            with st.container():
                st.markdown(f"""
                    <div style="background:#1a4a2e; border-radius:10px; padding:15px; margin:10px 0; border-left: 5px solid #2d6a4f;">
                        <div style="color:#f0ede8; font-weight:bold; font-size:18px;">Table: {o['table_name'] or 'Seating'}</div>
                        <div style="color:#f0ede8; font-size:14px;">Time: {o['order_time'][:19]}</div>
                        <div style="color:#f4d03f; font-weight:bold; font-size:20px;">₹{o['total_amount']:.2f}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Show order items
                items = get_order_items(o['id'])
                if items:
                    st.caption("Items: " + ", ".join([f"{it['quantity']}x {it['product_name']}" for it in items]))
                
                col1, col2 = st.columns([5, 1])
                with col2:
                    if st.button("✅ Complete", key=f"comp_{o['id']}"):
                        try:
                            requests.post(f"{API_BASE}/api/order/{o['id']}/complete", timeout=5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ── REPORTS ───────────────────────────────────────────────────────────────────
elif st.session_state.menu == "Reports":
    # Date range filter
    c1, c2, c3 = st.columns([2, 2, 1])
    start_date = c1.date_input("Start date", value=None)
    end_date = c2.date_input("End date", value=None)
    
    # Initialize data
    data = {"sessions": [], "orders": []}
    
    if c3.button("Apply", key="apply_filter"):
        params = {}
        if start_date:
            params["start_date"] = str(start_date)
        if end_date:
            params["end_date"] = str(end_date)
        try:
            resp = requests.get(f"{API_BASE}/api/sales_summary", params=params, timeout=5)
            data = resp.json() if resp.ok else {"sessions": [], "orders": []}
        except Exception as e:
            st.error(f"Error: {e}")
            data = {"sessions": [], "orders": []}
    else:
        data = get_sales_summary()
    
    with st.spinner("Loading top items..."):
        top_selling = get_top_selling()
    
    st.header("Sales Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Table Revenue")
        sessions_df = pd.DataFrame(data.get("sessions", []))
        if not sessions_df.empty:
            fig = px.bar(sessions_df, x="date", y="revenue", title="Table Revenue by Day", color_discrete_sequence=["#2d6a4f"])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(sessions_df, use_container_width=True)
            
            csv = sessions_df.to_csv(index=False)
            st.download_button("Download CSV", csv, "table_revenue.csv", "text/csv")
        else:
            st.info("No session data yet")

    with col2:
        st.subheader("Food/Drink Revenue")
        orders_df = pd.DataFrame(data.get("orders", []))
        if not orders_df.empty:
            fig = px.bar(orders_df, x="date", y="revenue", title="Order Revenue by Day", color_discrete_sequence=["#ff7f0e"])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(orders_df, use_container_width=True)
            
            csv = orders_df.to_csv(index=False)
            st.download_button("Download CSV", csv, "order_revenue.csv", "text/csv")
        else:
            st.info("No order data yet")
    
    st.divider()
    st.subheader("Top Selling Items")
    if top_selling:
        ts_df = pd.DataFrame(top_selling)
        fig = px.bar(ts_df, x="name", y="total_qty", title="Top Selling Items", color_discrete_sequence=["#e91e8c"])
        st.plotly_chart(fig, use_container_width=True)

# ── SETTINGS ───────────────────────────────────────────────────────────────────
elif st.session_state.menu == "Settings":
    st.header("⚙️ Settings")
    settings = get_settings()
    
    st.subheader("Cafe Settings")
    c1, c2 = st.columns(2)
    cafe_name = c1.text_input("Cafe Name", value=settings.get("cafe_name", "Snooker Cafe"))
    currency_symbol = c2.text_input("Currency Symbol", value=settings.get("currency_symbol", "₹"))
    c3, c4 = st.columns(2)
    default_min_minutes = c3.number_input("Default Min Minutes", value=int(settings.get("default_min_minutes", 20)), step=5)
    default_rate = c4.number_input("Default Rate/min (₹)", value=float(settings.get("default_rate_per_minute", 2.0)), step=0.5)
    
    if st.button("Save Settings"):
        try:
            requests.post(f"{API_BASE}/api/settings", params={
                "cafe_name": cafe_name,
                "currency_symbol": currency_symbol,
                "default_min_minutes": default_min_minutes,
                "default_rate_per_minute": default_rate
            }, timeout=5)
            st.success("Settings saved!")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.divider()
    st.subheader("Change Admin Password")
    current_pass = st.text_input("Current Password", type="password")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        try:
            resp = requests.get(f"{API_BASE}/api/change_password", params={
                "current": current_pass, "new": new_pass
            }, timeout=5)
            if resp.ok:
                st.success("Password changed!")
            else:
                st.error(resp.text)
        except Exception as e:
            st.error(f"Error: {e}")