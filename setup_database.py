import mysql.connector
from dotenv import load_dotenv
import os
import platform
from auth.user import User # Assuming User class has hash_password
from db_utils import get_connection_config # Keep this for connection config

# Load environment variables
load_dotenv()

# Use environment variables from .env file or set defaults if not found
if 'DB_HOST' not in os.environ:
    os.environ['DB_HOST'] = 'localhost'
if 'DB_USER' not in os.environ:
    os.environ['DB_USER'] = 'root'  # Use root as default
if 'DB_PASSWORD' not in os.environ:
    os.environ['DB_PASSWORD'] = 'root12345'  # Empty password by default
if 'DB_NAME' not in os.environ:
    # Changed default database name for SCNFBS project
    os.environ['DB_NAME'] = 'campus_navigation_booking'

# Print current working directory and env file location
print(f"Current working directory: {os.getcwd()}")
print(f"Environment variables set:")
print(f"DB_HOST: {os.environ.get('DB_HOST')}")
print(f"DB_USER: {os.environ.get('DB_USER')}")
print(f"DB_NAME: {os.environ.get('DB_NAME')}")

def create_database():
    try:
        # Get base configuration without database name
        config = get_connection_config()
        if 'database' in config:
            del config['database']  # Remove database name for initial connection

        print(f"\nAttempting to connect with:")
        print(f"Host: {config['host']}")
        print(f"User: {config['user']}")
        print(f"System: {platform.system()}")

        # MySQL server connection
        conn = mysql.connector.connect(**config)
        print("Connection successful!")

        # This is the line that now correctly returns dictionaries
        cursor = conn.cursor(dictionary=True) 

        # Drop existing database if it exists
        cursor.execute(f"DROP DATABASE IF EXISTS {os.environ.get('DB_NAME')}")
        print(f"Dropped database {os.environ.get('DB_NAME')} if it existed")

        # Create new database
        cursor.execute(f"CREATE DATABASE {os.environ.get('DB_NAME')}")
        print(f"Created database {os.environ.get('DB_NAME')}")

        cursor.execute(f"USE {os.environ.get('DB_NAME')}")
        print(f"Using database {os.environ.get('DB_NAME')}")

        # Define new tables for the Smart Campus Navigation and Facility Booking System
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARBINARY(255) NOT NULL,
                -- Updated roles for SCNFBS
                role ENUM('student', 'faculty', 'admin') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS buildings (
                building_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                address VARCHAR(200),
                description TEXT,
                latitude DECIMAL(10, 8), -- For map integration
                longitude DECIMAL(11, 8), -- For map integration
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS facilities (
                facility_id INT AUTO_INCREMENT PRIMARY KEY,
                building_id INT,
                name VARCHAR(100) NOT NULL, -- e.g., 'Study Room 301', 'Lab A', 'Gymnasium'
                type ENUM('Study Room', 'Lecture Hall', 'Lab', 'Sports Venue', 'Meeting Room', 'Other') NOT NULL,
                capacity INT DEFAULT 1,
                description TEXT,
                is_bookable BOOLEAN DEFAULT TRUE,
                -- Booking eligibility role
                booking_eligibility_role ENUM('student', 'faculty', 'admin', 'any') DEFAULT 'any',
                image_url VARCHAR(255),
                location_description VARCHAR(255), -- e.g., "3rd Floor, near elevator"
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (building_id) REFERENCES buildings(building_id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                facility_id INT,
                booking_number VARCHAR(50) UNIQUE NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                status ENUM('Confirmed', 'Cancelled', 'Pending Approval', 'Completed') DEFAULT 'Confirmed',
                purpose TEXT, -- e.g., 'Group Study Session', 'Lecture', 'Lab Experiment'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_recurring BOOLEAN DEFAULT FALSE, -- Supports recurring reservations
                -- recurring_rule_id INT NULL, -- Link to a future recurring_rules table if needed
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE
                -- Add FOREIGN KEY (recurring_rule_id) REFERENCES recurring_rules(rule_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS map_paths (
                path_id INT AUTO_INCREMENT PRIMARY KEY,
                start_point VARCHAR(255) NOT NULL, -- Can be building name, room name, or specific point
                end_point VARCHAR(255) NOT NULL,
                path_data JSON, -- Store complex path data (e.g., sequence of lat/lon points, or nodes)
                distance_meters DECIMAL(10, 2),
                duration_minutes DECIMAL(10, 2),
                is_accessible BOOLEAN DEFAULT FALSE, -- For accessible paths
                building_id INT NULL, -- If the path is internal to a specific building
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS booking_rules (
                rule_id INT AUTO_INCREMENT PRIMARY KEY,
                facility_type ENUM('Study Room', 'Lecture Hall', 'Lab', 'Sports Venue', 'Meeting Room', 'Other') NOT NULL UNIQUE,
                max_booking_duration_minutes INT DEFAULT 180, -- e.g., 3 hours
                min_booking_advance_hours INT DEFAULT 1, -- Book at least 1 hour in advance
                max_concurrent_bookings_per_user INT DEFAULT 1,
                can_recur BOOLEAN DEFAULT FALSE, -- Supports recurring reservations
                applies_to_roles VARCHAR(255) -- Comma-separated roles: 'student,faculty' for eligibility
            )
            """
        ]

        for table in tables:
            cursor.execute(table)
            print(f"Table created successfully: {table.split('IF NOT EXISTS')[1].split()[0]}")

        # Create an admin user
        admin_password = "admin123"
        admin_pwd_hash = User.hash_password(admin_password) # Uses the hash_password method from User class
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, created_at)
        VALUES ('admin', 'admin@campus.com', %s, 'admin', NOW())
        """, (admin_pwd_hash,))
        print(f"Admin user created with username 'admin' and password '{admin_password}'")

        # Add sample data for testing
        print("Adding sample data for testing...")

        # Add sample student and faculty users
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, created_at)
        VALUES
            ('student1', 'student1@campus.com', %s, 'student', NOW()),
            ('faculty1', 'faculty1@campus.com', %s, 'faculty', NOW()),
            ('student2', 'student2@campus.com', %s, 'student', NOW())
        """, (User.hash_password('student123'), User.hash_password('faculty123'), User.hash_password('student456'))) # Use dummy hashes

        # Add sample buildings
        cursor.execute("""
        INSERT INTO buildings (name, address, description, latitude, longitude)
        VALUES
            ('Main Library', '123 University Rd, University City', 'Central academic building with various study spaces and resources.', 24.4751, 54.3725),
            ('Engineering Block A', '456 Tech Lane, University City', 'Houses engineering labs, workshops, and lecture halls.', 24.4780, 54.3750),
            ('Sports Complex', '789 Athletics Way, University City', 'Facilities for various sports including gymnasiums and courts.', 24.4720, 54.3700)
        """)

        # Get building IDs for associating facilities
        cursor.execute("SELECT building_id, name FROM buildings")
        building_data = cursor.fetchall()
        building_ids = {b['name']: b['building_id'] for b in building_data}

        # Add sample facilities
        if 'Main Library' in building_ids:
            cursor.execute("""
            INSERT INTO facilities (building_id, name, type, capacity, description, is_bookable, booking_eligibility_role)
            VALUES
                (%s, 'Study Room 101', 'Study Room', 4, 'Quiet study room with whiteboards and monitors.', TRUE, 'student'),
                (%s, 'Study Room 102', 'Study Room', 6, 'Group study room with a large table.', TRUE, 'student'),
                (%s, 'Auditorium A', 'Lecture Hall', 150, 'Large lecture hall for major classes and events.', TRUE, 'faculty')
            """, (building_ids['Main Library'], building_ids['Main Library'], building_ids['Main Library']))

        if 'Engineering Block A' in building_ids:
            cursor.execute("""
            INSERT INTO facilities (building_id, name, type, capacity, description, is_bookable, booking_eligibility_role)
            VALUES
                (%s, 'Computer Lab 201', 'Lab', 30, 'Computer lab with specialized software for engineering students.', TRUE, 'faculty'),
                (%s, 'Research Lab B', 'Lab', 10, 'Advanced research laboratory.', TRUE, 'faculty'),
                (%s, 'Meeting Room 305', 'Meeting Room', 8, 'Small meeting room for faculty and staff.', TRUE, 'faculty')
            """, (building_ids['Engineering Block A'], building_ids['Engineering Block A'], building_ids['Engineering Block A']))

        if 'Sports Complex' in building_ids:
            cursor.execute("""
            INSERT INTO facilities (building_id, name, type, capacity, description, is_bookable, booking_eligibility_role)
            VALUES
                (%s, 'Basketball Court 1', 'Sports Venue', 20, 'Indoor basketball court.', TRUE, 'any'),
                (%s, 'Gymnasium A', 'Sports Venue', 50, 'Main gymnasium with fitness equipment.', FALSE, 'any') -- Example of non-bookable facility
            """, (building_ids['Sports Complex'], building_ids['Sports Complex']))

        # Add sample booking rules
        cursor.execute("""
        INSERT INTO booking_rules (facility_type, max_booking_duration_minutes, min_booking_advance_hours, max_concurrent_bookings_per_user, can_recur, applies_to_roles)
        VALUES
            ('Study Room', 240, 1, 1, TRUE, 'student'), -- Students can book study rooms for max 4 hours
            ('Lecture Hall', 480, 24, 0, TRUE, 'faculty'), -- Faculty can book lecture halls for max 8 hours
            ('Lab', 360, 12, 0, FALSE, 'faculty'), -- Labs cannot be recurring
            ('Sports Venue', 120, 2, 0, FALSE, 'any'), -- Sports venues for 2 hours
            ('Meeting Room', 180, 4, 1, TRUE, 'faculty')
        """)

        # --- THIS IS THE CORRECTED PART FOR map_paths ---
        cursor.execute("""
        INSERT INTO map_paths (start_point, end_point, path_data, distance_meters, duration_minutes, is_accessible, building_id, description)
        VALUES
            ('Main Library Entrance', 'Study Room 101', '{"route": ["path-segment-A", "path-segment-B"]}', 50.5, 1.2, TRUE, %s, 'Path from main entrance to Study Room 101'),
            ('Engineering Block A Main Door', 'Computer Lab 201', '{"route": ["path-segment-X", "path-segment-Y"]}', 120.0, 3.0, FALSE, %s, 'Standard path to Computer Lab 201'),
            ('Main Library', 'Engineering Block A', '{"route": ["campus-road-1", "campus-walk-2"]}', 750.0, 9.5, TRUE, NULL, 'Walkway between Main Library and Engineering Block A')
        """, (building_ids['Main Library'], building_ids['Engineering Block A'])) # Removed the 'None' parameter here
        # ---------------------------------------------------


        conn.commit()
        print("Database setup completed successfully with sample data for SCNFBS!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_database()