import hashlib
import os
from enum import Enum # Use Enum directly, auto is not strictly needed for explicit values
from db_utils import execute_query

class UserRole(Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"

class User:
    def __init__(self, user_id, username, email, role, is_active=True):
        self.user_id = user_id
        self.username = username
        self.email = email # Added email to User object
        self.role = UserRole(role) # Ensure role is an enum member
        self.is_authenticated = user_id is not None
        self.is_active = is_active # Added is_active to User object
        self._profile_data = None # Cache profile data to avoid repeated DB calls

    @staticmethod
    def hash_password(password, salt=None):
        """Hash a password for storing."""
        if salt is None:
            salt = os.urandom(32)  # 32 bytes salt
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',  # Hash algorithm
            password.encode('utf-8'),  # Convert password to bytes
            salt,  # Salt
            100000  # Number of iterations
        )
        
        return salt + password_hash  # Concatenate salt and hash
    
    @staticmethod
    def verify_password(stored_password_binary, provided_password):
        """Verify a stored password against a provided password."""
        # Ensure stored_password is bytes (from DB VARBINARY/BLOB)
        if isinstance(stored_password_binary, str):
            # If it's a hex string (from sha256.hexdigest()), convert it to bytes
            # This handles inconsistency from previous hashing if data already exists
            try:
                stored_password_binary = bytes.fromhex(stored_password_binary)
            except ValueError:
                # If it's not hex, assume it's direct binary (e.g., from pbkdf2)
                pass

        if len(stored_password_binary) < 32: # Minimum length for salt + hash
            # This might indicate an old SHA256 hash without salt
            # For robustness, try simple SHA256 comparison if it's too short for PBKDF2 format
            if hashlib.sha256(provided_password.encode()).hexdigest() == stored_password_binary.hex():
                return True
            return False

        salt = stored_password_binary[:32]  # First 32 bytes are salt
        stored_password_hash = stored_password_binary[32:]
        
        # Hash the provided password with the stored salt
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            100000
        )
        
        # Compare the calculated hash with the stored hash
        return new_hash == stored_password_hash
    
    @staticmethod
    def register(username, email, password, role): # Removed phone, address
        """Register a new user with the given details for SCNFBS."""
        # Check if username or email already exists
        existing_user = execute_query(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (username, email)
        )
        
        if existing_user:
            return False, "Username or email already exists."
        
        # Hash the password using the strong PBKDF2 method
        hashed_password_binary = User.hash_password(password) # Returns bytes
        
        # Insert the new user
        # Added is_active column with default TRUE for new registrations
        result = execute_query(
            """
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (%s, %s, %s, %s, NOW(), TRUE)
            """,
            (username, email, hashed_password_binary, role.value),
            fetch=False
        )
        
        if result is not None:
            # Get the user_id of the newly created user
            user_data = execute_query(
                "SELECT user_id FROM users WHERE username = %s",
                (username,)
            )
            
            if user_data:
                user_id = user_data[0]['user_id']
                
                # Create initial profile based on new role
                try:
                    if role == UserRole.STUDENT:
                        execute_query(
                            """
                            INSERT INTO students (user_id, student_id, major, enrollment_date)
                            VALUES (%s, %s, %s, NOW())
                            """,
                            (user_id, f"STU-{user_id:05d}", "Undeclared"), # Example default data
                            fetch=False
                        )
                    elif role == UserRole.FACULTY:
                        execute_query(
                            """
                            INSERT INTO faculty (user_id, faculty_id, department, title, hire_date)
                            VALUES (%s, %s, %s, %s, NOW())
                            """,
                            (user_id, f"FAC-{user_id:05d}", "General", "Lecturer"), # Example default data
                            fetch=False
                        )
                    # Admins do not get a separate profile table entry upon registration
                    # (they are typically created by other admins or during setup)
                except Exception as e:
                    print(f"Error creating initial profile for {role.value} (user_id: {user_id}): {e}")
                    # Consider rolling back the user creation if profile creation fails critically
                    # For now, it will proceed with just the user table entry
                    
            return True, "Account created successfully!"
        else:
            return False, "Failed to create account."
    
    @staticmethod
    def login(username_or_email, password):
        """Authenticate a user with the given credentials for SCNFBS."""
        user_data_result = execute_query(
            "SELECT user_id, username, email, password_hash, role, is_active FROM users WHERE username = %s OR email = %s",
            (username_or_email, username_or_email)
        )
        
        if not user_data_result:
            return None, "Invalid username or password."
        
        user_data = user_data_result[0]
        stored_hash_from_db = user_data['password_hash']

        # Verify password using the secure method
        if User.verify_password(stored_hash_from_db, password):
            user = User(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'], # Include email
                role=user_data['role'],
                is_active=user_data.get('is_active', True) # Get is_active status
            )
            user.is_authenticated = True
            if not user.is_active:
                return None, "Your account is currently inactive. Please contact an administrator."
            return user, "Login successful."
        else:
            return None, "Invalid username or password." # Generic message for security
    
    @staticmethod
    def get_by_id(user_id):
        """Retrieve a user by their ID."""
        user_data = execute_query(
            "SELECT user_id, username, email, role, is_active FROM users WHERE user_id = %s", # Include email, is_active
            (user_id,)
        )
        
        if not user_data:
            return None
        
        user_data = user_data[0]
        return User(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            role=UserRole(user_data['role']),
            is_active=user_data.get('is_active', True)
        )
    
    def get_profile(self):
        """Get the user's profile data based on their role for SCNFBS."""
        if self._profile_data:
            return self._profile_data # Return cached data if available

        profile_data = None
        # Always fetch common user info first
        user_common_info = execute_query("SELECT username, email FROM users WHERE user_id = %s", (self.user_id,))
        if user_common_info:
            profile_data = user_common_info[0]
        else:
            return {} # Should not happen if user object is valid

        if self.role == UserRole.STUDENT:
            student_profile = execute_query(
                "SELECT student_id, major, enrollment_date FROM students WHERE user_id = %s",
                (self.user_id,)
            )
            if student_profile:
                profile_data.update(student_profile[0])

        elif self.role == UserRole.FACULTY:
            faculty_profile = execute_query(
                "SELECT faculty_id, department, title, hire_date FROM faculty WHERE user_id = %s",
                (self.user_id,)
            )
            if faculty_profile:
                profile_data.update(faculty_profile[0])

        elif self.role == UserRole.ADMIN:
            # Admins generally don't have separate profile tables with unique fields.
            # Their profile is primarily their user account itself.
            # You might have an 'admins' table for additional info if needed, but for now,
            # we'll just use the common user info.
            admin_profile = execute_query(
                "SELECT admin_id FROM admins WHERE user_id = %s", # Assuming an admins table exists for consistency
                (self.user_id,)
            )
            if admin_profile:
                profile_data.update(admin_profile[0])
            else: # If no entry in 'admins' table, just use basic user info
                pass # profile_data already has username and email from common info

        self._profile_data = profile_data # Cache the data
        return self._profile_data
    
    def update_password(self, current_password, new_password):
        """Update the user's password."""
        # Retrieve the current hashed password (binary) from the database
        user_data = execute_query(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (self.user_id,)
        )
        
        if not user_data:
            return False, "User not found."
        
        stored_password_binary = user_data[0]['password_hash']
        
        # Verify current password using the secure method
        if not User.verify_password(stored_password_binary, current_password):
            return False, "Current password is incorrect."
        
        # Hash the new password using the strong PBKDF2 method
        new_password_hash = User.hash_password(new_password)
        
        # Update the password in the database
        result = execute_query(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (new_password_hash, self.user_id),
            fetch=False
        )
        
        if result is not None:
            return True, "Password updated successfully."
        else:
            return False, "Failed to update password."