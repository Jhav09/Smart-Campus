from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                            QPushButton, QFormLayout, QComboBox, QMessageBox,
                            QDialog, QHBoxLayout, QGroupBox, QRadioButton,
                            QGridLayout, QCheckBox, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont, QIcon, QKeyEvent
from auth.user import User, UserRole # Ensure UserRole enum is updated in auth/user.py
import json
import os
import re
import hashlib # Still useful for password hashing, though User.login might handle it

class LoginWindow(QWidget):
    login_successful = Signal(object)
    switch_to_register = Signal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_saved_login()
    
    def initUI(self):
        # Updated Title
        self.setWindowTitle("Smart Campus System - Login")
        self.setMinimumSize(350, 450)
        
        # Main layout with margins that scale with window size
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Logo/Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        # Add logo (ensure 'images/logo.png' is appropriate for campus system or update path)
        logo_label = QLabel()
        logo_pixmap = QPixmap("images/logo.png") # Adjust path if your logo is elsewhere
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setMinimumSize(100, 100)
            logo_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            header_layout.addWidget(logo_label)
            header_layout.addSpacing(10)
        else:
            print("Warning: Logo image not found at images/logo.png. Consider adding one for the Smart Campus System.")
        
        # Updated Title
        title = QLabel("Smart Campus System")
        title.setObjectName("app-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        
        subtitle = QLabel("Sign in to your account")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(20)
        
        # Form Section
        form_container = QWidget()
        form_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username or Email")
        self.username_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.remember_checkbox = QCheckBox("Remember Me")
        
        form_layout.addRow("Username/Email:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow(self.remember_checkbox)
        
        # Login Button
        login_btn = QPushButton("Login")
        login_btn.setObjectName("primary-button")
        login_btn.clicked.connect(self.attempt_login)
        login_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Register Link
        register_layout = QHBoxLayout()
        register_label = QLabel("Don't have an account?")
        register_btn = QPushButton("Register")
        register_btn.setFlat(True)
        register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        register_btn.clicked.connect(lambda: self.switch_to_register.emit())
        
        register_layout.addWidget(register_label)
        register_layout.addWidget(register_btn)
        register_layout.addStretch()
        
        # Connect Enter key press to login
        self.username_input.returnPressed.connect(self.attempt_login)
        self.password_input.returnPressed.connect(self.attempt_login)
        
        # Add all sections to main layout
        layout.addLayout(header_layout)
        layout.addWidget(form_container, 1)
        layout.addWidget(login_btn)
        layout.addLayout(register_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Set style (can be further customized for campus theme)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            #app-title {
                color: #2c3e50;
                font-size: 28px;
                font-weight: bold;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            #primary-button {
                background-color: #3498db;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            #primary-button:hover {
                background-color: #2980b9;
            }
            QPushButton:flat {
                color: #3498db;
                text-decoration: none;
            }
            QPushButton:flat:hover {
                text-decoration: underline;
            }
        """)
    
    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        # Hardcoded admin login for development (using new system's default admin)
        if username == "admin" and password == "admin123":
            admin_user = User(user_id=1, username="admin", email="admin@campus.com", role=UserRole.ADMIN)
            admin_user.is_authenticated = True # <--- Check indentation here

            if self.remember_checkbox.isChecked():
                self.save_login(username, password)
            else:
                self.clear_saved_login()

            self.login_successful.emit(admin_user)
            return
        
        # Try database login
        try:
            user, message = User.login(username, password)
            
            if user and user.is_active: # Ensure user is active
                if self.remember_checkbox.isChecked():
                    self.save_login(username, password)
                else:
                    self.clear_saved_login()
                    
                self.login_successful.emit(user)
            elif user and not user.is_active:
                QMessageBox.warning(self, "Login Failed", "Your account is currently inactive. Please contact an administrator.")
            else:
                QMessageBox.warning(self, "Login Failed", message)
        except Exception as e:
            print(f"Login error: {e}")
            QMessageBox.critical(self, "Database Error",
                               "Cannot connect to the database. Please check your database connection. " +
                               "Only the default admin account (admin/admin123) might be available in offline mode.")
    
    def load_saved_login(self):
        """Load saved login information if available"""
        try:
            if os.path.exists('settings/login.json'):
                with open('settings/login.json', 'r') as f:
                    login_data = json.load(f)
                
                self.username_input.setText(login_data.get('username', ''))
                self.password_input.setText(login_data.get('password', ''))
                self.remember_checkbox.setChecked(True)
        except Exception as e:
            print(f"Error loading saved login: {e}")
    
    def save_login(self, username, password):
        """Save login information to a file"""
        try:
            login_data = {
                'username': username,
                'password': password  # In a real application, encrypt this!
            }
            
            os.makedirs('settings', exist_ok=True)
            
            with open('settings/login.json', 'w') as f:
                json.dump(login_data, f)
        except Exception as e:
            print(f"Error saving login info: {e}")
    
    def clear_saved_login(self):
        """Remove saved login information"""
        try:
            if os.path.exists('settings/login.json'):
                os.remove('settings/login.json')
        except Exception as e:
            print(f"Error clearing saved login: {e}")


class RegisterWindow(QWidget):
    register_successful = Signal(User)
    switch_to_login = Signal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        # Updated Title
        self.setWindowTitle("Smart Campus System - Register")
        self.setMinimumSize(400, 500) # Adjusted minimum height
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Logo/Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        # Add logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("images/logo.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setMinimumSize(100, 100)
            logo_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            header_layout.addWidget(logo_label)
            header_layout.addSpacing(10)
        
        # Updated Title
        title = QLabel("Smart Campus System")
        title.setObjectName("app-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        
        subtitle = QLabel("Create a new account")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(15)
        
        # Form Section
        form_container = QWidget()
        form_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.username_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Your email address")
        self.email_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Removed phone and address inputs
        # self.phone_input = QLineEdit()
        # self.phone_input.setPlaceholderText("Your phone number")
        # self.phone_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # self.address_input = QLineEdit()
        # self.address_input.setPlaceholderText("Your address (optional)")
        # self.address_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Choose a password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm your password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # User Role Selection - Updated for SCNFBS
        role_group = QGroupBox("I want to register as a:")
        role_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        role_layout = QHBoxLayout()
        
        self.student_radio = QRadioButton("Student")
        self.faculty_radio = QRadioButton("Faculty/Staff")
        
        self.student_radio.setChecked(True) # Default selection for campus system
        
        role_layout.addWidget(self.student_radio)
        role_layout.addWidget(self.faculty_radio)
        # Removed Delivery radio button
        
        role_group.setLayout(role_layout)
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Email:", self.email_input)
        # form_layout.addRow("Phone:", self.phone_input) # Removed
        # form_layout.addRow("Address (optional):", self.address_input) # Removed
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Confirm Password:", self.confirm_password_input)
        
        # Register Button
        register_btn = QPushButton("Create Account")
        register_btn.setObjectName("primary-button")
        register_btn.clicked.connect(self.register)
        register_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Login Link
        login_layout = QHBoxLayout()
        login_label = QLabel("Already have an account?")
        login_btn = QPushButton("Login")
        login_btn.setFlat(True)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(lambda: self.switch_to_login.emit())
        
        login_layout.addWidget(login_label)
        login_layout.addWidget(login_btn)
        login_layout.addStretch()
        
        # Add all sections to main layout
        layout.addLayout(header_layout)
        layout.addWidget(form_container, 1)
        layout.addWidget(role_group) # Role selection added below form
        layout.addWidget(register_btn)
        layout.addLayout(login_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Set style (can be further customized for campus theme)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            #app-title {
                color: #2c3e50;
                font-size: 28px;
                font-weight: bold;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QGroupBox {
                font-weight: bold;
                color: #2c3e50; /* Ensure text color is visible */
                border: 1px solid #ddd; /* Add border for better visual separation */
                border-radius: 5px;
                margin-top: 10px; /* Space from above element */
                padding-top: 15px; /* Space for title */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QRadioButton {
                padding: 5px;
                color: #2c3e50; /* Ensure text color is visible */
            }
            #primary-button {
                background-color: #3498db;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            #primary-button:hover {
                background-color: #2980b9;
            }
            QPushButton:flat {
                color: #3498db;
                text-decoration: none;
            }
            QPushButton:flat:hover {
                text-decoration: underline;
            }
        """)
    
    def register(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        # phone = self.phone_input.text().strip() # Removed
        # address = self.address_input.text().strip() # Removed
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Validate inputs
        if not username or not email or not password or not confirm_password:
            QMessageBox.warning(self, "Warning", "Please fill in all required fields (Username, Email, Password).")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Warning", "Passwords do not match.")
            return

        # Basic email format check
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return
        
        # Determine user role - Updated for SCNFBS
        if self.student_radio.isChecked():
            role = UserRole.STUDENT
        elif self.faculty_radio.isChecked():
            role = UserRole.FACULTY
        else:
            # Fallback (shouldn't happen with default selected)
            role = UserRole.STUDENT
        
        # Attempt to register
        # Removed phone and address from User.register call
        success, message = User.register(username, email, password, role)
        
        if success:
            QMessageBox.information(self, "Success", message)
            
            # Log in the user
            user, _ = User.login(username, password)
            if user:
                self.register_successful.emit(user)
            else:
                self.switch_to_login.emit()
        else:
            QMessageBox.critical(self, "Error", message)
