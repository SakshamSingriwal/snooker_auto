#!/usr/bin/env python
"""
Test script for snooker_auto upgrades.
Tests inventory, combos, and order flows.
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from backend import database as db
from backend import inventory
from backend import combos

def test_inventory():
    print("\n=== Testing Inventory Module ===")
    
    # Initialize DB
    db.init_db()
    
    # Add ingredient
    iid = inventory.add_ingredient("Burger Bun", "pcs", 20)
    print(f"✓ Added ingredient 'Burger Bun' with ID {iid}")
    
    # Get ingredient
    ing = inventory.get_ingredient(iid)
    assert ing["name"] == "Burger Bun"
    print(f"✓ Retrieved ingredient: {ing}")
    
    # Update stock
    inventory.update_ingredient(iid, current_stock=50)
    ing = inventory.get_ingredient(iid)
    assert ing["current_stock"] == 50
    print(f"✓ Updated stock to {ing['current_stock']}")
    
    # Test low stock
    inventory.update_ingredient(iid, current_stock=5)
    low = inventory.get_low_stock_ingredients()
    assert any(i["id"] == iid for i in low)
    print(f"✓ Low stock detection works: {len(low)} items below threshold")
    
    return True

def test_recipes():
    print("\n=== Testing Recipe Module ===")
    
    # Create a product first
    db.add_product("Burger", "food", 150)
    
    # Add ingredients
    bun_id = inventory.add_ingredient("Burger Bun", "pcs", 20)
    patty_id = inventory.add_ingredient("Patty", "pcs", 20)
    
    # Set recipe
    products = db.get_products()
    burger = [p for p in products if p["name"] == "Burger"][0]
    
    inventory.set_recipe(burger["id"], [(bun_id, 1), (patty_id, 1)])
    recipe = inventory.get_recipe_for_product(burger["id"])
    print(f"✓ Set recipe: {len(recipe)} ingredients")
    
    # Check availability (should fail - only 1 bun/patty in stock)
    available, missing = inventory.check_ingredients_available(burger["id"], 2)
    assert not available
    assert missing is not None
    print(f"✓ Correctly detected insufficient stock: {missing}")
    
    return True

def test_combos():
    print("\n=== Testing Combo Module ===")
    
    # Add combo
    cid = combos.add_combo("Lunch Special", None, 50, "lunch", "Burger + Fries")
    print(f"✓ Created combo with ID {cid}")
    
    # Add combo items
    products = db.get_products()
    burger = [p for p in products if p["name"] == "Burger"]
    if burger:
        combos.add_combo_item(cid, burger[0]["id"], 1)
        print(f"✓ Added item to combo")
    
    # Get combos
    all_combos = combos.get_combos()
    assert len(all_combos) >= 1
    print(f"✓ Retrieved {len(all_combos)} combos")
    
    # Test suggestions
    suggestions = combos.generate_smart_combos()
    print(f"✓ Generated {len(suggestions)} smart combo suggestions")
    
    return True

def run_all_tests():
    print("=" * 50)
    print("Snooker Auto Upgrade Tests")
    print("=" * 50)
    
    try:
        test_inventory()
        test_recipes()
        test_combos()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_all_tests()