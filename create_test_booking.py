import random
import mysql.connector
from datetime import datetime, timedelta
from db_utils import get_connection_config, execute_query
import uuid
from decimal import Decimal

def create_test_order():
    print("Creating a random test order...")
    
    try:
        # Step 1: Get a random restaurant
        restaurants = execute_query("SELECT restaurant_id, name FROM restaurants")
        if not restaurants:
            print("No restaurants found in database.")
            return
        
        restaurant = random.choice(restaurants)
        restaurant_id = restaurant['restaurant_id']
        restaurant_name = restaurant['name']
        print(f"Selected restaurant: {restaurant_name} (ID: {restaurant_id})")
        
        # Step 2: Get a random menu item from this restaurant
        menu_items = execute_query(
            "SELECT menu_id, dish_name, price FROM menus WHERE restaurant_id = %s",
            (restaurant_id,)
        )
        
        if not menu_items:
            print(f"No menu items found for restaurant {restaurant_name}.")
            return
        
        # Select 1-3 random items from menu
        selected_items = random.sample(menu_items, min(random.randint(1, 3), len(menu_items)))
        print(f"Selected {len(selected_items)} menu items:")
        for item in selected_items:
            print(f"  - {item['dish_name']} ({float(item['price'])} AED)")
        
        # Step 3: Get a random customer
        customers = execute_query("SELECT customer_id, name, address FROM customers")
        if not customers:
            print("No customers found in database.")
            return
        
        customer = random.choice(customers)
        customer_id = customer['customer_id']
        customer_name = customer['name']
        delivery_address = customer['address']
        print(f"Selected customer: {customer_name} (ID: {customer_id})")
        
        # Step 4: Calculate order totals
        subtotal = sum(float(item['price']) for item in selected_items)
        delivery_fee = random.uniform(5.0, 15.0)
        tax = subtotal * 0.05  # 5% tax
        total_amount = subtotal + delivery_fee + tax
        
        # Generate a unique order number
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Random order status (mostly active statuses for testing)
        status_options = ['Pending', 'Confirmed', 'Preparing', 'On Delivery']
        delivery_status = random.choice(status_options)
        
        # Current time for order time
        order_time = datetime.now()
        estimated_delivery = order_time + timedelta(minutes=random.randint(30, 90))
        
        # Step 5: Create the order
        order_query = """
        INSERT INTO orders (
            customer_id, restaurant_id, order_number, delivery_address,
            delivery_status, order_time, estimated_delivery_time,
            subtotal, delivery_fee, tax, total_amount, payment_method
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        order_params = (
            customer_id, restaurant_id, order_number, delivery_address,
            delivery_status, order_time, estimated_delivery,
            subtotal, delivery_fee, tax, total_amount,
            random.choice(['Credit Card', 'Cash on Delivery', 'Digital Wallet'])
        )
        
        order_id = execute_query(order_query, order_params, fetch=False)
        
        if not order_id:
            print("Failed to create order.")
            return
        
        print(f"Created order with ID: {order_id} and number: {order_number}")
        
        # Step 6: Create order items
        for item in selected_items:
            quantity = random.randint(1, 3)
            unit_price = float(item['price'])
            total_price = unit_price * quantity
            
            item_query = """
            INSERT INTO order_items (
                order_id, menu_id, quantity, unit_price, total_price
            ) VALUES (%s, %s, %s, %s, %s)
            """
            
            item_params = (order_id, item['menu_id'], quantity, unit_price, total_price)
            execute_query(item_query, item_params, fetch=False)
        
        print(f"Order created successfully with status: {delivery_status}")
        print(f"Order details:")
        print(f"  - Order #: {order_number}")
        print(f"  - Restaurant: {restaurant_name}")
        print(f"  - Customer: {customer_name}")
        print(f"  - Total: {total_amount:.2f} AED")
        print(f"  - Status: {delivery_status}")
        
        return order_id, order_number
        
    except Exception as e:
        print(f"Error creating test order: {e}")
        return None

if __name__ == "__main__":
    create_test_order() 