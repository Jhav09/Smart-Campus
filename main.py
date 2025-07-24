import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon
from db_utils import test_connection, reset_debug_state

# Assuming you have updated auth/user.py to include these roles
from auth.user import User, UserRole
from ui.login import LoginWindow, RegisterWindow
# Import your new dashboards
# You will need to create these files and folders:
# ui/student/dashboard.py
# ui/faculty/dashboard.py
# ui/admin/dashboard.py
from ui.student.dashboard import StudentDashboard
from ui.faculty.dashboard import FacultyDashboard # This will replace Restaurant/Delivery
from ui.admin.dashboard import AdminDashboard

class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        # Updated window title for the new project
        self.setWindowTitle("Smart Campus Navigation and Facility Booking System")
        self.setMinimumSize(800, 600)  # Smaller minimum size
        self.resize(1200, 800)  # Initial size but can be resized

        # Make window resizable
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        # Initialize stacked widget to manage different screens
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create instances of screens
        self.login_window = LoginWindow()
        self.register_window = RegisterWindow()

        # Add screens to stacked widget
        self.stacked_widget.addWidget(self.login_window)
        self.stacked_widget.addWidget(self.register_window)

        # Connect signals
        self.login_window.login_successful.connect(self.handle_login)
        self.login_window.switch_to_register.connect(lambda: self.stacked_widget.setCurrentWidget(self.register_window))

        self.register_window.register_successful.connect(self.handle_login)
        self.register_window.switch_to_login.connect(lambda: self.stacked_widget.setCurrentWidget(self.login_window))

        # Start with login window
        self.stacked_widget.setCurrentWidget(self.login_window)

        # Center the window on the screen
        self.center_on_screen()

    def center_on_screen(self):
        """Center the window on the screen"""
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

        # Store the screen dimensions to use for responsive layouts
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

    def handle_login(self, user):
        """Handle user login by showing the appropriate dashboard"""
        if not user.is_authenticated:
            return

        # Reset debug state for a new session
        reset_debug_state()

        # Create and show the appropriate dashboard based on user role
        # Updated roles and dashboard mappings for SCNFBS
        if user.role == UserRole.STUDENT:
            dashboard = StudentDashboard(user)
            self.stacked_widget.addWidget(dashboard)
            self.stacked_widget.setCurrentWidget(dashboard)
            dashboard.logout_requested.connect(self.handle_logout)
        elif user.role == UserRole.FACULTY: # Combines old RESTAURANT and DELIVERY roles
            dashboard = FacultyDashboard(user)
            self.stacked_widget.addWidget(dashboard)
            self.stacked_widget.setCurrentWidget(dashboard)
            dashboard.logout_requested.connect(self.handle_logout)
        # Removed UserRole.DELIVERY as it's not applicable to SCNFBS, or can be repurposed
        elif user.role == UserRole.ADMIN:
            dashboard = AdminDashboard(user)
            self.stacked_widget.addWidget(dashboard)
            self.stacked_widget.setCurrentWidget(dashboard)
            dashboard.logout_requested.connect(self.handle_logout)

    def handle_logout(self):
        """Handle user logout by returning to login screen"""
        # Get current widget and remove it from stacked widget
        current_widget = self.stacked_widget.currentWidget()

        # Switch to login window
        self.stacked_widget.setCurrentWidget(self.login_window)

        # Remove the dashboard widget if it's not the login or register window
        if current_widget not in [self.login_window, self.register_window]:
            self.stacked_widget.removeWidget(current_widget)
            current_widget.deleteLater()

if __name__ == "__main__":
    # Add debug logging for environment variables and connection details
    print("=" * 60)
    print("STARTUP DEBUG - Environment variables:")
    print(f"DB_HOST: {os.environ.get('DB_HOST', 'Not set')}")
    print(f"DB_USER: {os.environ.get('DB_USER', 'Not set')}")
    print(f"DB_PASSWORD: {'*******' if os.environ.get('DB_PASSWORD') else 'Not set'}")
    # Updated DB_NAME for SCNFBS
    print(f"DB_NAME: {os.environ.get('DB_NAME', 'Not set')}")
    print("=" * 60)

    # Initialize application
    app = QApplication(sys.argv)

    # Set application-wide stylesheet (can be customized for SCNFBS theme)
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2c3e50;
            border: none;
            margin: 0;
            padding: 0;
        }
        QWidget {
            background-color: transparent;
            font-family: -apple-system, BlinkMacMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
        }
        QStackedWidget, #content-area {
            background-color: #f8f9fa;
        }
        QPushButton {
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:disabled {
            background-color: #95a5a6;
        }
        QLineEdit, QComboBox, QSpinBox {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: white;
            color: black;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
            border: 1px solid #3498db;
        }
        QLabel {
            color: #2c3e50;
        }
    """)

    # Test database connection
    if not test_connection():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Database Error")
        msg.setText("Failed to connect to database")
        msg.setInformativeText("Please check your database settings and make sure MySQL is running.")
        msg.setDetailedText("""
Common issues:
1. MySQL server might not be running
2. Incorrect username or password in .env file
3. Database 'campus_navigation_booking' might not exist # Updated database name
4. Network connectivity issues

Please check the console output for more details.
""")
        msg.exec()
        sys.exit(1)

    # Start the application
    main_app = MainApplication()
    main_app.show()
    sys.exit(app.exec())
    