import random
from datetime import datetime, timedelta
from db_utils import execute_query # Ensure db_utils is updated for SCNFBS
from create_test_booking import create_test_booking # Import your new test booking creation script

def simulate_booking_lifecycle():
    print("Simulating a booking lifecycle...")

    try:
        # Step 1: Create a test booking
        print("Creating test booking...")
        booking_id, booking_number = create_test_booking()
        
        if not booking_id:
            print("Failed to create a test booking. Aborting simulation.")
            return
            
        print(f"Successfully created booking: {booking_number} (ID: {booking_id})")
        
        # Step 2: Simulate a scenario for the booking (e.g., complete or cancel)
        # In a real system, 'Completed' would happen after the end_time has passed.
        # 'Cancelled' can happen at any time before the booking starts.
        scenario = random.choice(['complete', 'cancel'])

        if scenario == 'complete':
            print(f"Simulating completion for booking #{booking_number}...")
            # For simulation, we'll mark it completed.
            # In a real system, this would be a check triggered after booking end_time.
            complete_query = """
            UPDATE bookings 
            SET status = 'Completed',
                updated_at = NOW()
            WHERE booking_id = %s
            """
            result = execute_query(complete_query, (booking_id,), fetch=False)
            
            if result is None:
                print(f"Failed to mark booking #{booking_number} as completed.")
                return
                
            print(f"Booking #{booking_number} marked as 'Completed'.")
        
        elif scenario == 'cancel':
            print(f"Simulating cancellation for booking #{booking_number}...")
            cancel_query = """
            UPDATE bookings 
            SET status = 'Cancelled',
                updated_at = NOW()
            WHERE booking_id = %s
            """
            result = execute_query(cancel_query, (booking_id,), fetch=False)
            
            if result is None:
                print(f"Failed to mark booking #{booking_number} as cancelled.")
                return
                
            print(f"Booking #{booking_number} marked as 'Cancelled'.")
        
        print("\nBooking details for verification:")
        
        # Get complete booking details
        booking_details = execute_query("""
            SELECT b.*, u.username, f.name as facility_name, bu.name as building_name
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            JOIN facilities f ON b.facility_id = f.facility_id
            JOIN buildings bu ON f.building_id = bu.building_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        
        if booking_details:
            bk = booking_details[0]
            print(f"Booking ID: {bk['booking_id']}")
            print(f"Booking Number: {bk['booking_number']}")
            print(f"User: {bk['username']}")
            print(f"Facility: {bk['facility_name']} ({bk['building_name']})")
            print(f"Purpose: {bk['purpose']}")
            print(f"Start Time: {bk['start_time']}")
            print(f"End Time: {bk['end_time']}")
            print(f"Current Status: {bk['status']}")
        
        return booking_id
        
    except Exception as e:
        print(f"Error simulating booking lifecycle: {e}")
        return None

if __name__ == "__main__":
    simulate_booking_lifecycle()