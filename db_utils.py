import mysql.connector
from dotenv import load_dotenv
import os
import platform
from datetime import datetime, timedelta
import uuid # Needed for generating unique booking numbers

# Load environment variables from .env file first
load_dotenv()

# Then set defaults if not found
if 'DB_HOST' not in os.environ:
    os.environ['DB_HOST'] = 'localhost'
if 'DB_USER' not in os.environ:
    os.environ['DB_USER'] = 'root'
if 'DB_PASSWORD' not in os.environ:
    os.environ['DB_PASSWORD'] = ''
if 'DB_NAME' not in os.environ:
    # Changed default database name for SCNFBS
    os.environ['DB_NAME'] = 'campus_navigation_booking'

# Flag to track if we've shown debug information in the current session
_debug_shown = False

def reset_debug_state():
    """Reset the debug state - call this at the start of a new session"""
    global _debug_shown
    _debug_shown = False

def get_connection_config():
    """Get database connection configuration based on platform"""
    config = {
        'host': os.environ.get('DB_HOST'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'use_pure': True  # Use pure Python implementation for compatibility
    }

    # Add database name if it exists (not for initial setup)
    if os.environ.get('DB_NAME'):
        config['database'] = os.environ.get('DB_NAME')

    # Handle different authentication methods based on platform
    if platform.system() == 'Darwin':  # macOS
        # Try without auth_plugin first
        try:
            test_conn = mysql.connector.connect(**config)
            test_conn.close()
            return config
        except mysql.connector.Error:
            # If that fails, try with auth_plugin
            config['auth_plugin'] = 'caching_sha2_password'

    # For Windows, specify auth_plugin as we've set to mysql_native_password
    if platform.system() == 'Windows':
        config['auth_plugin'] = 'mysql_native_password'

    return config

def test_connection():
    """Test the database connection and return True if successful, False otherwise"""
    print("\nTesting database connection...")
    print(f"Platform: {platform.system()}")
    print(f"Using configuration:")
    config = get_connection_config()
    for key, value in config.items():
        if key != 'password':  # Don't print password
            print(f"  {key}: {value}")

    try:
        connection = mysql.connector.connect(**config)
        if connection and connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✓ Connected to MySQL Server version {db_info}")
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()[0]
            print(f"✓ Connected to database: {db_name}")
            cursor.close()
            connection.close()
            return True
        return False
    except mysql.connector.Error as err:
        print(f"✗ Error testing connection: {err}")
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("  Please check your username and password")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            print("  Database does not exist")
        return False

def get_db_connection():
    """Get database connection using platform-specific configuration"""
    global _debug_shown

    try:
        config = get_connection_config()

        # Only show debug info the first time in this session
        first_connection = not _debug_shown
        if first_connection:
            debug_config = {k: v for k, v in config.items() if k != 'password'}
            print(f"DEBUG - Connecting with config: {debug_config}")
            _debug_shown = True

        connection = mysql.connector.connect(**config)

        # Show connection established message the first time
        if first_connection:
            print(f"DEBUG - Connection established successfully")

        return connection
    except mysql.connector.Error as err:
        print(f"ERROR - Database connection error: {err}")
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("ERROR - Check your username and password")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            print("ERROR - Database does not exist")
        return None
    except Exception as e:
        print(f"ERROR - Unexpected error during connection: {e}")
        return None

def execute_query(query, params=None, fetch=True):
    try:
        connection = get_db_connection()
        if not connection:
            print("Database connection failed. Check your database settings or server status.")
            return None

        try:
            cursor = connection.cursor(dictionary=True)

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.lastrowid

            return result
        except mysql.connector.Error as err:
            error_msg = f"Error executing query: {err}"
            print(error_msg)

            connection.rollback()
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# --- NEW FUNCTIONS FOR SCNFBS ---

def search_buildings(search_term=None, campus_area=None):
    """Search for buildings on campus."""
    try:
        query = "SELECT * FROM buildings WHERE 1=1"
        params = []

        if search_term:
            query += " AND (name LIKE %s OR address LIKE %s OR description LIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])

        if campus_area:
            # Assuming campus_area could be part of the address or a separate field
            query += " AND address LIKE %s"
            params.append(f"%{campus_area}%")

        query += " ORDER BY name ASC"
        return execute_query(query, params)
    except Exception as e:
        print(f"Error searching buildings: {e}")
        return None

def search_facilities(search_term=None, building_id=None, facility_type=None,
                      capacity=None, min_capacity=None, max_capacity=None):
    """
    Search for facilities (rooms, labs, etc.) based on criteria.
    This replaces `search_menu_items`.
    """
    try:
        query = """
        SELECT f.*, b.name as building_name
        FROM facilities f
        JOIN buildings b ON f.building_id = b.building_id
        WHERE 1=1
        """
        params = []

        if search_term:
            query += " AND (f.name LIKE %s OR f.description LIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        if building_id:
            query += " AND f.building_id = %s"
            params.append(building_id)

        if facility_type:
            query += " AND f.type = %s"
            params.append(facility_type)

        if capacity: # Specific capacity
            query += " AND f.capacity = %s"
            params.append(capacity)
        if min_capacity: # Minimum capacity
            query += " AND f.capacity >= %s"
            params.append(min_capacity)
        if max_capacity: # Maximum capacity
            query += " AND f.capacity <= %s"
            params.append(max_capacity)

        query += " ORDER BY f.name ASC"

        return execute_query(query, params)
    except Exception as e:
        print(f"Error searching facilities: {e}")
        return None

def get_facility_availability(facility_id, check_date):
    """
    Checks the availability of a specific facility for a given date.
    Returns occupied time slots.
    """
    try:
        query = """
        SELECT start_time, end_time
        FROM bookings
        WHERE facility_id = %s
        AND DATE(start_time) = %s
        AND status IN ('Confirmed', 'Pending Approval')
        ORDER BY start_time
        """
        params = (facility_id, check_date)
        return execute_query(query, params)
    except Exception as e:
        print(f"Error getting facility availability: {e}")
        return None

def create_booking(user_id, facility_id, start_time, end_time, purpose):
    """
    Creates a new facility booking.
    """
    try:
        # Check for booking conflicts before proceeding
        conflict_query = """
        SELECT booking_id FROM bookings
        WHERE facility_id = %s
        AND start_time < %s
        AND end_time > %s
        AND status IN ('Confirmed', 'Pending Approval')
        """
        conflict_params = (facility_id, end_time, start_time)
        conflicting_bookings = execute_query(conflict_query, conflict_params)

        if conflicting_bookings:
            print("Error: Facility is already booked during this time.")
            return None

        # Generate a unique booking number
        booking_number = f"BKG-{uuid.uuid4().hex[:8].upper()}"

        insert_query = """
        INSERT INTO bookings (
            user_id, facility_id, booking_number, start_time, end_time,
            status, purpose
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        insert_params = (
            user_id, facility_id, booking_number, start_time, end_time,
            'Confirmed', purpose
        )

        booking_id = execute_query(insert_query, insert_params, fetch=False)
        print(f"Booking {booking_number} created successfully for facility ID {facility_id}")

        # ✅ Fallback if booking_id is 0 or None
        if booking_id is None or booking_id == 0:
            latest_booking = execute_query("""
                SELECT booking_id FROM bookings
                WHERE user_id = %s AND facility_id = %s AND start_time = %s AND end_time = %s
                ORDER BY booking_id DESC LIMIT 1
            """, (user_id, facility_id, start_time, end_time))

            if latest_booking:
                return latest_booking[0]['booking_id']
            else:
                return None
        else:
            return booking_id

    except Exception as e:
        print(f"Error creating booking: {e}")
        return None


def cancel_booking(booking_id):
    """Allows a user to cancel a booking."""
    try:
        query = "UPDATE bookings SET status = 'Cancelled', updated_at = NOW() WHERE booking_id = %s"
        result = execute_query(query, (booking_id,), fetch=False)
        return result is not None # True if update was successful
    except Exception as e:
        print(f"Error cancelling booking: {e}")
        return False

def get_user_bookings(user_id, status=None, start_date=None, end_date=None):
    """
    Retrieves all bookings for a specific user.
    This replaces `search_orders` for customer/user view.
    """
    try:
        query = """
        SELECT b.*, f.name as facility_name, bu.name as building_name
        FROM bookings b
        JOIN facilities f ON b.facility_id = f.facility_id
        JOIN buildings bu ON f.building_id = bu.building_id
        WHERE b.user_id = %s
        """
        params = [user_id]

        if status and status != "All":
            query += " AND b.status = %s"
            params.append(status)

        if start_date:
            query += " AND DATE(b.start_time) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(b.end_time) <= %s"
            params.append(end_date)

        query += " ORDER BY b.start_time DESC"
        return execute_query(query, params)
    except Exception as e:
        print(f"Error getting user bookings: {e}")
        return None

def get_facility_usage_report(facility_id=None, start_date=None, end_date=None, facility_type=None):
    """
    Generates reports on facility usage. For Admin.
    This replaces analytics/reporting in food delivery system.
    """
    try:
        query = """
        SELECT
            f.name AS facility_name,
            f.type AS facility_type,
            b.name AS building_name,
            COUNT(bk.booking_id) AS total_bookings,
            SUM(TIMESTAMPDIFF(MINUTE, bk.start_time, bk.end_time)) AS total_duration_minutes,
            AVG(TIMESTAMPDIFF(MINUTE, bk.start_time, bk.end_time)) AS avg_duration_minutes
        FROM bookings bk
        JOIN facilities f ON bk.facility_id = f.facility_id
        JOIN buildings b ON f.building_id = b.building_id
        WHERE bk.status = 'Confirmed' OR bk.status = 'Completed'
        """
        params = []

        if facility_id:
            query += " AND f.facility_id = %s"
            params.append(facility_id)
        if facility_type:
            query += " AND f.type = %s"
            params.append(facility_type)
        if start_date:
            query += " AND bk.start_time >= %s"
            params.append(start_date)
        if end_date:
            query += " AND bk.end_time <= %s"
            params.append(end_date)

        query += """
        GROUP BY f.facility_id, f.name, f.type, b.name
        ORDER BY total_bookings DESC
        """
        return execute_query(query, params)
    except Exception as e:
        print(f"Error generating facility usage report: {e}")
        return None

def search_map_paths(start_point_desc, end_point_desc, is_accessible=None):
    """
    Searches for navigation paths between two points on campus.
    This is a new core navigation function.
    """
    try:
        # This is a simplified search. A real map system would involve complex graph traversal.
        # Here we assume start_point_desc and end_point_desc directly map to 'start_point'/'end_point'
        # in the map_paths table or are used to find relevant building/facility coordinates.
        query = "SELECT * FROM map_paths WHERE start_point LIKE %s AND end_point LIKE %s"
        params = [f"%{start_point_desc}%", f"%{end_point_desc}%"]

        if is_accessible is not None:
            query += " AND is_accessible = %s"
            params.append(is_accessible)

        query += " ORDER BY distance_meters ASC"
        return execute_query(query, params)
    except Exception as e:
        print(f"Error searching map paths: {e}")
        return None

# --- Admin-specific functions to manage data ---
def add_building(name, address, description=None, latitude=None, longitude=None):
    """Adds a new building to the database."""
    try:
        query = """
        INSERT INTO buildings (name, address, description, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (name, address, description, latitude, longitude)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error adding building: {e}")
        return None

def update_building(building_id, name=None, address=None, description=None, latitude=None, longitude=None):
    """Updates an existing building's information."""
    try:
        updates = []
        params = []
        if name:
            updates.append("name = %s")
            params.append(name)
        if address:
            updates.append("address = %s")
            params.append(address)
        if description:
            updates.append("description = %s")
            params.append(description)
        if latitude:
            updates.append("latitude = %s")
            params.append(latitude)
        if longitude:
            updates.append("longitude = %s")
            params.append(longitude)

        if not updates:
            print("No updates provided for building.")
            return None

        query = f"UPDATE buildings SET {', '.join(updates)}, updated_at = NOW() WHERE building_id = %s"
        params.append(building_id)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error updating building: {e}")
        return None

def delete_building(building_id):
    """Deletes a building and its associated facilities."""
    try:
        query = "DELETE FROM buildings WHERE building_id = %s"
        return execute_query(query, (building_id,), fetch=False)
    except Exception as e:
        print(f"Error deleting building: {e}")
        return None

def add_facility(building_id, name, facility_type, capacity, description=None,
                 is_bookable=True, booking_eligibility_role='any', image_url=None, location_description=None):
    """Adds a new facility (room, lab etc.) to the database."""
    try:
        query = """
        INSERT INTO facilities (building_id, name, type, capacity, description,
                                is_bookable, booking_eligibility_role, image_url, location_description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (building_id, name, facility_type, capacity, description,
                  is_bookable, booking_eligibility_role, image_url, location_description)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error adding facility: {e}")
        return None

def update_facility(facility_id, building_id=None, name=None, facility_type=None, capacity=None, description=None,
                    is_bookable=None, booking_eligibility_role=None, image_url=None, location_description=None):
    """Updates an existing facility's information."""
    try:
        updates = []
        params = []
        if building_id:
            updates.append("building_id = %s")
            params.append(building_id)
        if name:
            updates.append("name = %s")
            params.append(name)
        if facility_type:
            updates.append("type = %s")
            params.append(facility_type)
        if capacity is not None: # Can be 0
            updates.append("capacity = %s")
            params.append(capacity)
        if description:
            updates.append("description = %s")
            params.append(description)
        if is_bookable is not None:
            updates.append("is_bookable = %s")
            params.append(is_bookable)
        if booking_eligibility_role:
            updates.append("booking_eligibility_role = %s")
            params.append(booking_eligibility_role)
        if image_url:
            updates.append("image_url = %s")
            params.append(image_url)
        if location_description:
            updates.append("location_description = %s")
            params.append(location_description)

        if not updates:
            print("No updates provided for facility.")
            return None

        query = f"UPDATE facilities SET {', '.join(updates)}, updated_at = NOW() WHERE facility_id = %s"
        params.append(facility_id)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error updating facility: {e}")
        return None

def delete_facility(facility_id):
    """Deletes a facility."""
    try:
        query = "DELETE FROM facilities WHERE facility_id = %s"
        return execute_query(query, (facility_id,), fetch=False)
    except Exception as e:
        print(f"Error deleting facility: {e}")
        return None

def add_booking_rule(facility_type, max_booking_duration_minutes, min_booking_advance_hours,
                      max_concurrent_bookings_per_user, can_recur, applies_to_roles):
    """Adds a new booking rule for a facility type."""
    try:
        query = """
        INSERT INTO booking_rules (facility_type, max_booking_duration_minutes, min_booking_advance_hours,
                                   max_concurrent_bookings_per_user, can_recur, applies_to_roles)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (facility_type, max_booking_duration_minutes, min_booking_advance_hours,
                  max_concurrent_bookings_per_user, can_recur, applies_to_roles)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error adding booking rule: {e}")
        return None

def get_booking_rule(facility_type):
    """Retrieves booking rules for a specific facility type."""
    try:
        query = "SELECT * FROM booking_rules WHERE facility_type = %s"
        return execute_query(query, (facility_type,))
    except Exception as e:
        print(f"Error getting booking rule: {e}")
        return None

def update_booking_rule(rule_id, max_booking_duration_minutes=None, min_booking_advance_hours=None,
                        max_concurrent_bookings_per_user=None, can_recur=None, applies_to_roles=None):
    """Updates an existing booking rule."""
    try:
        updates = []
        params = []
        if max_booking_duration_minutes is not None:
            updates.append("max_booking_duration_minutes = %s")
            params.append(max_booking_duration_minutes)
        if min_booking_advance_hours is not None:
            updates.append("min_booking_advance_hours = %s")
            params.append(min_booking_advance_hours)
        if max_concurrent_bookings_per_user is not None:
            updates.append("max_concurrent_bookings_per_user = %s")
            params.append(max_concurrent_bookings_per_user)
        if can_recur is not None:
            updates.append("can_recur = %s")
            params.append(can_recur)
        if applies_to_roles:
            updates.append("applies_to_roles = %s")
            params.append(applies_to_roles)

        if not updates:
            print("No updates provided for booking rule.")
            return None

        query = f"UPDATE booking_rules SET {', '.join(updates)} WHERE rule_id = %s"
        params.append(rule_id)
        return execute_query(query, params, fetch=False)
    except Exception as e:
        print(f"Error updating booking rule: {e}")
        return None

def delete_booking_rule(rule_id):
    """Deletes a booking rule."""
    try:
        query = "DELETE FROM booking_rules WHERE rule_id = %s"
        return execute_query(query, (rule_id,), fetch=False)
    except Exception as e:
        print(f"Error deleting booking rule: {e}")
        return None

# --- End of NEW FUNCTIONS ---ere ? 