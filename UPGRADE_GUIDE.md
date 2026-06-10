# Snooker Auto Upgrade Guide

Version 2.0 - Inventory, Recipes, Combos & Enhanced UX

## New Features Overview

### 1. Advanced Inventory Management
- **Stock Tracking**: Track product and ingredient stock levels
- **Recipe System**: Define recipes for menu items with ingredient quantities
- **Low Stock Alerts**: Automatic detection and warnings when stock falls below threshold

### 2. Vendor Management
- Track suppliers for ingredients
- Lead time tracking for reordering

### 3. Smart Combos
- Time-based combo offers (e.g., Lunch Special)
- Automated combo suggestions based on order co-occurrence analysis

### 4. Enhanced Customer Experience
- Reorder favorites using localStorage
- Order status polling (pending → preparing → ready)
- Special instructions for orders

### 5. Admin Dashboard Enhancements
- Inventory tab with stock management
- Vendors tab for supplier management
- Combos tab with smart suggestions
- Order tagging (VIP, Urgent, Large Group)
- Order status workflow

---

## Migration Instructions

### Step 1: Backup Existing Database
```bash
cp snooker_auto/data/snooker.db snooker_auto/data/snooker.db.backup
```

### Step 2: Run Migration
```bash
python migrate_db.py
```

This adds:
- `current_stock`, `min_stock_threshold`, `stock_unit` to products table
- `status`, `special_instructions`, `tag` to orders table
- New tables: `ingredients`, `recipe_ingredients`, `vendors`, `combos`, `combo_items`

### Step 3: Install New Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Start Application
```bash
python run.py
```

---

## Cron Job Setup (Smart Combos)

To automatically generate combo suggestions daily at 6 AM:

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task → "Snooker Auto Combo Generation"
3. Trigger: Daily at 6:00 AM
4. Action: Run `python` with argument:
   ```
   -c "import requests; requests.post('http://localhost:8000/api/combos/generate_smart')"
   ```

### Linux/Mac (crontab)
```bash
crontab -e
# Add line:
0 6 * * * curl -X POST http://localhost:8000/api/combos/generate_smart
```

---

## Usage Guide

### Admin Dashboard - Inventory Tab
1. **View Low Stock Alerts**: Top of page shows all ingredients below threshold
2. **Add Ingredient**: Enter name, unit (pcs/kg/L), and minimum threshold
3. **Update Stock**: Use the Vendors tab to update stock levels after delivery

### Admin Dashboard - Recipes Tab
1. Navigate to "Menu Items" → Edit a product → Add recipe ingredients
2. Or use API endpoints to set recipes programmatically

### Admin Dashboard - Combos Tab
1. **Active Combos**: Shows currently available combo offers
2. **All Combos**: Manage active/inactive combos
3. **Smart Suggestions**: Shows automatically generated combo ideas based on order patterns

### Customer Frontend
1. **Favorites**: Previously ordered items appear at top for quick re-order
2. **Order Tracking**: After placing order, status bar shows progress
3. **Notifications**: Browser notifications when order is ready

---

## API Endpoints Added

### Inventory
- `GET /api/inventory` - List all ingredients
- `GET /api/inventory/low_stock` - Get low stock items
- `POST /api/inventory/ingredient` - Add ingredient
- `PUT /api/inventory/ingredient/{id}` - Update ingredient

### Recipes
- `GET /api/recipes` - List all recipes
- `GET /api/recipes/product/{id}` - Get recipe for product
- `POST /api/recipes/product/{id}` - Set recipe (format: "ing_id:qty,id2:qty2")

### Vendors
- `GET /api/vendors` - List vendors
- `POST /api/vendors` - Add vendor
- `PUT /api/vendors/{id}` - Update vendor

### Combos
- `GET /api/combos` - List combos
- `POST /api/combos` - Create combo
- `POST /api/combos/generate_smart` - Get smart suggestions
- `PUT /api/combos/{id}/activate` - Activate/deactivate combo

### Orders (Enhanced)
- `PUT /api/order/{id}/status` - Update order status
- `GET /api/order/{id}/status` - Get order status
- `PUT /api/order/{id}/edit` - Edit order items
- `PUT /api/order/{id}/tag` - Set order tag

---

## Troubleshooting

### Database Migration Errors
- Ensure `snooker_auto/data/` directory exists
- Check file permissions on `snooker.db`

### Inventory Not Deducting
- Verify recipes are set for products
- Check ingredient stock levels before ordering

### Combo Suggestions Not Generating
- Need at least 3 orders in last 7 days with co-occurring items
- Check `/api/reports` for sufficient order data