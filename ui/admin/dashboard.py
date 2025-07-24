from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox, QRadioButton, QGroupBox,
    QDateEdit, QTabWidget, QCheckBox, QProgressDialog, QApplication, QProgressBar,
    QMenu, QSpinBox, QTextEdit, QFileDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QDate, QDateTime, QTimer
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap

# Using matplotlib for charts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import time
import re
import os
import uuid # For generating unique IDs, especially for booking numbers
import datetime
from db_utils import execute_query, get_booking_rule # Import new db_utils functions
from functools import partial

class AdminDashboard(QWidget):
    logout_requested = Signal()

    def __init__(self, user):
        super().__init__()
        self.user = user

        # Set up auto-refresh timer for real-time updates
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(500)  # Refresh every 0.5 seconds

        # Flag to track if we should skip refresh
        self._skip_refresh = False

        self.initUI()

    def initUI(self):
        # Updated window title
        self.setWindowTitle("Smart Campus - Administration Dashboard")

        # Main layout
        main_layout = QHBoxLayout(self)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(250)
        sidebar.setMinimumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)

        # User info section
        user_info = QFrame()
        user_info.setObjectName("user-info")
        user_info_layout = QVBoxLayout(user_info)

        welcome_label = QLabel(f"Welcome, Admin")
        welcome_label.setObjectName("welcome-label")
        welcome_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        user_info_layout.addWidget(welcome_label)
        sidebar_layout.addWidget(user_info)

        # Navigation buttons - Updated for SCNFBS
        nav_buttons = [
            {"text": "Dashboard", "icon": "📊", "slot": self.show_dashboard},
            {"text": "Users", "icon": "👥", "slot": self.manage_users},
            {"text": "Buildings", "icon": "🏛️", "slot": self.manage_buildings}, # New
            {"text": "Facilities", "icon": "📍", "slot": self.manage_facilities}, # New
            {"text": "Bookings", "icon": "📅", "slot": self.manage_bookings}, # Renamed from Orders
            {"text": "Reports", "icon": "📈", "slot": self.view_reports},
            {"text": "Settings", "icon": "⚙️", "slot": self.system_settings}
        ]

        for btn_info in nav_buttons:
            btn = QPushButton(f"{btn_info['icon']} {btn_info['text']}")
            btn.setObjectName("nav-button")
            btn.clicked.connect(btn_info["slot"])
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("logout-button")
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)

        # Content area
        self.content_area = QStackedWidget()

        # Create all pages - Updated for SCNFBS
        self.dashboard_page = self.create_dashboard_page()
        self.buildings_page = self.create_buildings_page() # New
        self.facilities_page = self.create_facilities_page() # New
        self.users_page = self.create_users_page()
        self.bookings_page = self.create_bookings_page() # Renamed from orders
        self.reports_page = self.create_reports_page()
        self.settings_page = self.create_settings_page()

        # Add pages to stacked widget - Updated for SCNFBS
        self.content_area.addWidget(self.dashboard_page)
        self.content_area.addWidget(self.buildings_page)
        self.content_area.addWidget(self.facilities_page)
        self.content_area.addWidget(self.users_page)
        self.content_area.addWidget(self.bookings_page)
        self.content_area.addWidget(self.reports_page)
        self.content_area.addWidget(self.settings_page)

        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_area)

        # Apply styles (kept largely similar, adjust as needed)
        self.setStyleSheet("""
            #sidebar {
                background-color: #2c3e50;
                border-radius: 0px;
                padding: 10px;
            }
            #user-info {
                border-bottom: 1px solid #34495e;
                padding-bottom: 15px;
                margin-bottom: 15px;
            }
            #welcome-label {
                color: white;
            }
            #nav-button {
                text-align: left;
                padding: 12px;
                border-radius: 5px;
                background-color: transparent;
                color: white;
                font-size: 14px;
            }
            #nav-button:hover {
                background-color: #34495e;
            }
            #logout-button {
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            #logout-button:hover {
                background-color: #c0392b;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QPushButton#action-button {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton#action-button:hover {
                background-color: #2980b9;
            }
            QPushButton#delete-button {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton#delete-button:hover {
                background-color: #c0392b;
            }
        """)

        # Start with dashboard
        self.show_dashboard()

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header
        header = QLabel("Administration Dashboard")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 24))

        # Stats overview - Updated for SCNFBS
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)

        # Load actual stats from database with fallbacks - Updated queries
        try:
            facility_count = execute_query("SELECT COUNT(*) as count FROM facilities")
            facility_count = facility_count[0]['count'] if facility_count else 0
        except Exception as e:
            print(f"Error getting facility count: {e}")
            facility_count = 0

        try:
            user_count = execute_query("SELECT COUNT(*) as count FROM users WHERE role IN ('student', 'faculty')")
            user_count = user_count[0]['count'] if user_count else 0
        except Exception as e:
            print(f"Error getting user count: {e}")
            user_count = 0

        try:
            today_bookings = execute_query("SELECT COUNT(*) as count FROM bookings WHERE DATE(start_time) = CURDATE() AND status != 'Cancelled'")
            today_bookings = today_bookings[0]['count'] if today_bookings else 0
        except Exception as e:
            print(f"Error getting today's bookings: {e}")
            today_bookings = 0

        try:
            # Total confirmed booking hours (sum of duration)
            total_booking_hours = execute_query("SELECT SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60 as total FROM bookings WHERE status = 'Confirmed'")
            total_booking_hours = total_booking_hours[0]['total'] if total_booking_hours and total_booking_hours[0]['total'] is not None else 0
        except Exception as e:
            print(f"Error getting total booking hours: {e}")
            total_booking_hours = 0

        # Create stat cards and store references for refreshing
        self.stat_widgets = {}

        stat_cards = [
            {"id": "facility_count", "title": "Total Facilities", "value": str(facility_count), "icon": "📍"},
            {"id": "user_count", "title": "Active Users", "value": str(user_count), "icon": "👥"},
            {"id": "today_bookings", "title": "Bookings Today", "value": str(today_bookings), "icon": "📅"},
            {"id": "total_booking_hours", "title": "Total Booked Hrs", "value": f"{total_booking_hours:.1f} hrs", "icon": "⏰"}
        ]

        for card in stat_cards:
            card_widget = QFrame()
            card_widget.setObjectName("stat-card")
            card_layout = QVBoxLayout(card_widget)

            title = QLabel(f"{card['icon']} {card['title']}")
            title.setObjectName("stat-title")

            value = QLabel(card["value"])
            value.setObjectName("stat-value")
            value.setFont(QFont("Arial", 20, QFont.Weight.Bold))

            # Store reference to value label for refreshing
            self.stat_widgets[card["id"] + "_value"] = value

            card_layout.addWidget(title)
            card_layout.addWidget(value)

            stats_layout.addWidget(card_widget)

        # Recent Bookings section - Updated from Recent Orders
        recent_bookings_label = QLabel("Recent Bookings")
        recent_bookings_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        self.recent_bookings_table = QTableWidget()
        self.recent_bookings_table.setColumnCount(5)
        self.recent_bookings_table.setHorizontalHeaderLabels(["Booking #", "User", "Facility", "Time", "Status"])
        self.recent_bookings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_bookings_table.horizontalHeader().setStretchLastSection(True)
        self.recent_bookings_table.setAlternatingRowColors(True)
        self.recent_bookings_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")


        # Load recent bookings with fallback - Updated query
        try:
            recent_bookings = execute_query("""
                SELECT bk.booking_id, bk.booking_number, u.username as user_name, f.name as facility_name,
                       bk.start_time, bk.end_time, bk.status
                FROM bookings bk
                JOIN users u ON bk.user_id = u.user_id
                JOIN facilities f ON bk.facility_id = f.facility_id
                ORDER BY bk.created_at DESC
                LIMIT 5
            """)

            if recent_bookings:
                self.recent_bookings_table.setRowCount(len(recent_bookings))
                for i, booking in enumerate(recent_bookings):
                    self.recent_bookings_table.setItem(i, 0, QTableWidgetItem(booking['booking_number']))
                    self.recent_bookings_table.setItem(i, 1, QTableWidgetItem(booking['user_name']))
                    self.recent_bookings_table.setItem(i, 2, QTableWidgetItem(booking['facility_name']))
                    
                    time_str = f"{booking['start_time'].strftime('%m-%d %H:%M')} to {booking['end_time'].strftime('%H:%M')}"
                    self.recent_bookings_table.setItem(i, 3, QTableWidgetItem(time_str))

                    status_item = QTableWidgetItem(booking['status'])
                    if booking['status'] == 'Confirmed':
                        status_item.setForeground(Qt.GlobalColor.darkGreen)
                    elif booking['status'] == 'Cancelled':
                        status_item.setForeground(Qt.GlobalColor.red)
                    elif booking['status'] == 'Pending Approval':
                        status_item.setForeground(Qt.GlobalColor.darkYellow)
                    self.recent_bookings_table.setItem(i, 4, status_item)
            else:
                self.recent_bookings_table.setRowCount(0)

        except Exception as e:
            print(f"Error loading recent bookings: {e}")
            self.recent_bookings_table.setRowCount(1)
            info_item = QTableWidgetItem("Database connection error. Please check your database connection.")
            self.recent_bookings_table.setSpan(0, 0, 1, 5)
            self.recent_bookings_table.setItem(0, 0, info_item)

        # Add to layout
        layout.addWidget(header)
        layout.addWidget(stats_frame)
        layout.addSpacing(20)
        layout.addWidget(recent_bookings_label)
        layout.addWidget(self.recent_bookings_table)

        page.setStyleSheet("""
            #stat-card {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                min-height: 120px;
                border: 1px solid #ddd;
            }
            #stat-title {
                color: #7f8c8d;
                font-size: 16px;
            }
            #stat-value {
                color: #2c3e50;
                font-size: 24px;
                font-weight: bold;
            }
        """)

        return page

    # --- NEW: Building Management Page ---
    def create_buildings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header_layout = QHBoxLayout()
        header = QLabel("Building Management")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)

        add_building_btn = QPushButton("Add New Building")
        add_building_btn.setObjectName("action-button")
        add_building_btn.clicked.connect(self.add_edit_building)
        header_layout.addStretch()
        header_layout.addWidget(add_building_btn)

        self.building_table = QTableWidget()
        self.building_table.setColumnCount(5)
        self.building_table.setHorizontalHeaderLabels(["ID", "Name", "Address", "Description", "Actions"])
        self.building_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.building_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.building_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.building_table.setAlternatingRowColors(True)
        self.building_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        layout.addLayout(header_layout)
        layout.addWidget(self.building_table)
        self.load_buildings()
        return page

    def load_buildings(self):
        self.building_table.setRowCount(0)
        try:
            buildings = execute_query("SELECT * FROM buildings ORDER BY name ASC")
            if not buildings:
                self.display_no_data_message(self.building_table, "No buildings found.")
                return

            self.building_table.setRowCount(len(buildings))
            for row_idx, building in enumerate(buildings):
                self.building_table.setItem(row_idx, 0, QTableWidgetItem(str(building['building_id'])))
                self.building_table.setItem(row_idx, 1, QTableWidgetItem(building['name']))
                self.building_table.setItem(row_idx, 2, QTableWidgetItem(building['address']))
                self.building_table.setItem(row_idx, 3, QTableWidgetItem(building['description'] or 'N/A'))

                buttons_widget = QWidget()
                buttons_layout = QHBoxLayout(buttons_widget)
                buttons_layout.setContentsMargins(0, 0, 0, 0)
                buttons_layout.setSpacing(5)

                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("action-button")
                edit_btn.clicked.connect(lambda checked, b=building: self.add_edit_building(b))

                delete_btn = QPushButton("Delete")
                delete_btn.setObjectName("delete-button")
                delete_btn.clicked.connect(lambda checked, bid=building['building_id']: self.delete_building(bid))

                buttons_layout.addWidget(edit_btn)
                buttons_layout.addWidget(delete_btn)
                self.building_table.setCellWidget(row_idx, 4, buttons_widget)
        except Exception as e:
            print(f"Error loading buildings: {e}")
            self.display_db_error_message(self.building_table, "Failed to load buildings.")

    def add_edit_building(self, building=None):
        dialog = BuildingDialog(self, building)
        if dialog.exec():
            self.load_buildings() # Refresh table after add/edit

    def delete_building(self, building_id):
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this building? This will also delete all associated facilities and their bookings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # db_utils.delete_building handles cascading deletion
                result = execute_query("DELETE FROM buildings WHERE building_id = %s", (building_id,), fetch=False)
                if result is not None:
                    QMessageBox.information(self, "Success", "Building and associated data deleted successfully.")
                    self.load_buildings()
                    # Also refresh facilities in case any were deleted
                    self.load_facilities()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete building.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    # --- NEW: Facility Management Page (Replaces Restaurant Management) ---
    def create_facilities_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header_layout = QHBoxLayout()
        header = QLabel("Facility Management")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)

        add_facility_btn = QPushButton("Add New Facility")
        add_facility_btn.setObjectName("action-button")
        add_facility_btn.clicked.connect(self.add_edit_facility)
        header_layout.addStretch()
        header_layout.addWidget(add_facility_btn)

        # Filter by Building and Type
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(20)

        self.facility_building_filter = QComboBox()
        self.facility_building_filter.addItem("All Buildings", None)  # Add option for all
        self.load_buildings_into_combo(self.facility_building_filter)
        self.facility_building_filter.currentIndexChanged.connect(self.filter_facilities)

        filter_layout.addStretch()
        filter_layout.addWidget(QLabel("Filter by Building:"))
        filter_layout.addWidget(self.facility_building_filter)



        self.facility_building_filter.setStyleSheet("""
            QComboBox {
                background-color: transparent;
                border: none;
                color: black;
                font-weight: normal;
            }
            QComboBox::drop-down {
                border: none;
                width: 15px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/down-arrow.png);  /* or remove this line to use system default arrow */
                width: 10px;
                height: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
            }
        """)

        self.facility_type_filter = QComboBox()
        self.facility_type_filter.addItems(["All Types", "Study Room", "Lecture Hall", "Lab", "Sports Venue", "Meeting Room", "Other"])
        self.facility_type_filter.currentIndexChanged.connect(self.filter_facilities)

        filter_layout.addStretch()
        filter_layout.addWidget(QLabel("Filter by Type:"))
        filter_layout.addWidget(self.facility_type_filter)

        self.facility_type_filter.setStyleSheet("""
            QComboBox {
                background: transparent;
                border: none;
                color: black;
                font-weight: normal;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
            }
        """)


        header_layout.addLayout(filter_layout) # Add filters to the header

        self.facility_table = QTableWidget()
        self.facility_table.setColumnCount(8)
        self.facility_table.setHorizontalHeaderLabels(["ID", "Building", "Name", "Type", "Capacity", "Bookable", "Eligible Role", "Actions"])
        self.facility_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.facility_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.facility_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.facility_table.setAlternatingRowColors(True)
        self.facility_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        layout.addLayout(header_layout)
        layout.addWidget(self.facility_table)
        self.load_facilities()
        return page

    def load_buildings_into_combo(self, combo_box):
        """Helper to load buildings into a QComboBox."""
        try:
            buildings = execute_query("SELECT building_id, name FROM buildings ORDER BY name")
            for building in buildings:
                combo_box.addItem(building['name'], building['building_id'])
        except Exception as e:
            print(f"Error loading buildings for combo box: {e}")

    def load_facilities(self, building_id=None, facility_type=None):
        self.facility_table.setRowCount(0)
        try:
            query = """
                SELECT f.*, b.name as building_name
                FROM facilities f
                JOIN buildings b ON f.building_id = b.building_id
                WHERE 1=1
            """
            params = []
            if building_id:
                query += " AND f.building_id = %s"
                params.append(building_id)
            if facility_type and facility_type != "All Types":
                query += " AND f.type = %s"
                params.append(facility_type)

            query += " ORDER BY f.name ASC"
            facilities = execute_query(query, params)

            if not facilities:
                self.display_no_data_message(self.facility_table, "No facilities found matching criteria.")
                return

            self.facility_table.setRowCount(len(facilities))
            for row_idx, facility in enumerate(facilities):
                self.facility_table.setItem(row_idx, 0, QTableWidgetItem(str(facility['facility_id'])))
                self.facility_table.setItem(row_idx, 1, QTableWidgetItem(facility['building_name']))
                self.facility_table.setItem(row_idx, 2, QTableWidgetItem(facility['name']))
                self.facility_table.setItem(row_idx, 3, QTableWidgetItem(facility['type']))
                self.facility_table.setItem(row_idx, 4, QTableWidgetItem(str(facility['capacity'])))
                self.facility_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

                bookable_item = QTableWidgetItem("Yes" if facility['is_bookable'] else "No")
                bookable_item.setForeground(Qt.GlobalColor.darkGreen if facility['is_bookable'] else Qt.GlobalColor.red)
                self.facility_table.setItem(row_idx, 5, bookable_item)

                self.facility_table.setItem(row_idx, 6, QTableWidgetItem(facility['booking_eligibility_role'].capitalize()))

                buttons_widget = QWidget()
                buttons_layout = QHBoxLayout(buttons_widget)
                buttons_layout.setContentsMargins(0, 0, 0, 0)
                buttons_layout.setSpacing(5)

                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("action-button")
                edit_btn.clicked.connect(lambda checked, f=facility: self.add_edit_facility(f))

                delete_btn = QPushButton("Delete")
                delete_btn.setObjectName("delete-button")
                delete_btn.clicked.connect(lambda checked, fid=facility['facility_id']: self.delete_facility(fid))

                buttons_layout.addWidget(edit_btn)
                buttons_layout.addWidget(delete_btn)
                self.facility_table.setCellWidget(row_idx, 7, buttons_widget)
        except Exception as e:
            print(f"Error loading facilities: {e}")
            self.display_db_error_message(self.facility_table, "Failed to load facilities.")

    def filter_facilities(self):
        building_id = self.facility_building_filter.currentData() # Gets the stored data (building_id)
        facility_type = self.facility_type_filter.currentText()
        if facility_type == "All Types":
            facility_type = None # Pass None to query if "All Types" is selected
        self.load_facilities(building_id, facility_type)

    def add_edit_facility(self, facility=None):
        dialog = FacilityDialog(self, facility)
        if dialog.exec():
            self.load_facilities() # Refresh table after add/edit

    def delete_facility(self, facility_id):
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this facility? This will also delete all associated bookings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = execute_query("DELETE FROM facilities WHERE facility_id = %s", (facility_id,), fetch=False)
                if result is not None:
                    QMessageBox.information(self, "Success", "Facility and associated bookings deleted successfully.")
                    self.load_facilities()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete facility.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    # --- User Management Page ---
    def create_users_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("User Management")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)

        # Filter by role - Updated for SCNFBS roles
        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Users", "Students", "Faculty", "Admins"])
        self.role_filter.currentIndexChanged.connect(self.filter_users)

        header_layout.addStretch()
        header_layout.addWidget(QLabel("Filter by role:"))
        header_layout.addWidget(self.role_filter)

        self.role_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: #2c3e50;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView {
                background-color: #3498db;  /* Blue background for dropdown options */
                color: white;               /* White text for options */
                selection-background-color: #2980b9; /* Darker blue when hovering */
                selection-color: white;
            }
        """)

        #Filter by date:
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDisplayFormat("yyyy-MM-dd")
        self.date_filter.setDate(QDate.currentDate().addMonths(-1))
        self.date_filter.dateChanged.connect(self.filter_users)

        header_layout.addWidget(QLabel("Registered after:"))
        header_layout.addWidget(self.date_filter)

        self.date_filter.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: #2c3e50;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }

            QCalendarWidget QWidget {
                background-color: #3498db;
                color: white;
            }

            QCalendarWidget QAbstractItemView {
                selection-background-color: #2980b9;
                selection-color: white;
            }
        """)

         # Table for users
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role", "Created", "Actions"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.users_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")
        # Load users
        self.load_users()

        # Add to layout
        layout.addLayout(header_layout)
        layout.addSpacing(10)
        layout.addWidget(self.users_table)

        return page

    def load_users(self, role_filter="All Users",date_filter=None):
        # Map filter to database role - Updated for SCNFBS roles
        role_map = {
            "All Users": None,
            "Students": "student",
            "Faculty": "faculty",
            "Admins": "admin"
        }

        self.users_table.setRowCount(0)

        try:
            # Build query based on filter
            
            if role_map[role_filter] and date_filter:
                query = "SELECT * FROM users WHERE role = %s AND DATE(created_at) >= %s ORDER BY created_at DESC"
                users = execute_query(query, (role_map[role_filter], date_filter))
            if role_map[role_filter]:
                query = "SELECT * FROM users WHERE role = %s ORDER BY created_at DESC"
                users = execute_query(query, (role_map[role_filter],))
            elif date_filter:
                query = "SELECT * FROM users WHERE DATE(created_at) >= %s ORDER BY created_at DESC"
                users = execute_query(query, (date_filter,))
            else:
                query = "SELECT * FROM users ORDER BY created_at DESC"
                users = execute_query(query)

            if not users:
                self.display_no_data_message(self.users_table, "No users found.")
                return

            self.users_table.setRowCount(len(users))
            for i, user in enumerate(users):
                # User details
                user_id = QTableWidgetItem(str(user['user_id']))
                username = QTableWidgetItem(user['username'])
                email = QTableWidgetItem(user.get('email', 'N/A'))
                role = QTableWidgetItem(user['role'].capitalize())
                created = QTableWidgetItem(user['created_at'].strftime("%Y-%m-%d") if user.get('created_at') else 'N/A')

                self.users_table.setItem(i, 0, user_id)
                self.users_table.setItem(i, 1, username)
                self.users_table.setItem(i, 2, email)
                self.users_table.setItem(i, 3, role)
                self.users_table.setItem(i, 4, created)

                # Action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)

                # View button (generic for now, can be specific if needed)
                view_btn = QPushButton("View")
                view_btn.setObjectName("action-button")
                view_btn.clicked.connect(lambda _, uid=user['user_id']: self.view_user(uid))
                
                # Suspend/Activate button (for non-admin users)
                if user['role'] != 'admin':
                    is_active = user.get('is_active', True)
                    status_btn = QPushButton("Suspend" if is_active else "Activate")
                    status_btn.setObjectName("warning-button" if is_active else "action-button") # Use warning for suspend
                    status_btn.setStyleSheet(f"""
                        text-align: center;
                        background-color: {'#f39c12' if is_active else '#2ecc71'};
                        color: white;
                        border-radius: 4px;
                        padding: 8px 15px;
                        margin: 2px;
                        font-size: 12px;
                        font-weight: bold;
                    """)
                    status_btn.clicked.connect(lambda checked, uid=user['user_id'], act=not is_active: self.toggle_user_status(uid, act))
                    actions_layout.addWidget(status_btn)

                delete_btn = QPushButton("Delete")
                delete_btn.setObjectName("delete-button")
                delete_btn.clicked.connect(lambda _, uid=user['user_id']: self.delete_user(uid))

                actions_layout.addWidget(view_btn)
                actions_layout.addWidget(delete_btn)

                self.users_table.setCellWidget(i, 5, actions_widget)
        except Exception as e:
            print(f"Error loading users: {e}")
            self.display_db_error_message(self.users_table)

    def filter_users(self, index = None):
        role_text = self.role_filter.currentText()
        selected_date = self.date_filter.date().toPython()
    
        self.load_users(role_text, selected_date)

    def view_user(self, user_id):
        user = execute_query("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not user:
            QMessageBox.warning(self, "Error", "User not found")
            return
        user = user[0]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"User Details - {user['username']}")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog { background-color: #2c3e50; color: white; }
            QLabel { color: white; font-size: 12px; }
            QGroupBox { color: white; border: 1px solid #7f8c8d; border-radius: 4px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)

        layout = QVBoxLayout(dialog)

        basic_info = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_info)
        basic_layout.addRow("Username:", QLabel(user['username']))
        basic_layout.addRow("Email:", QLabel(user['email']))
        basic_layout.addRow("Role:", QLabel(user['role'].capitalize()))
        basic_layout.addRow("Account Status:", QLabel("Active" if user.get('is_active') else "Inactive"))

        # Role-specific info (No need for separate tables like customers/restaurants/delivery)
        # All additional details would be within the 'users' table or derived from bookings
        role_info = QGroupBox(f"{user['role'].capitalize()} Specifics")
        role_layout = QFormLayout(role_info)

        # Example: For students/faculty, show total bookings
        if user['role'] in ['student', 'faculty']:
            bookings_count = execute_query("SELECT COUNT(*) as count FROM bookings WHERE user_id = %s", (user_id,))
            if bookings_count:
                role_layout.addRow("Total Bookings:", QLabel(str(bookings_count[0]['count'])))
        
        layout.addWidget(basic_info)
        layout.addWidget(role_info)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()
    
    def toggle_user_status(self, user_id, active_status):
        """Activate or suspend a user account (student/faculty)"""
        status_text = "activate" if active_status else "suspend"
        
        reply = QMessageBox.question(
            self, f"Confirm {status_text.capitalize()}", 
            f"Are you sure you want to {status_text} this user account?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = execute_query(
                "UPDATE users SET is_active = %s WHERE user_id = %s",
                (active_status, user_id),
                fetch=False
            )
            
            if result is not None:
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"User account {'activated' if active_status else 'suspended'} successfully"
                )
                # Refresh current view
                self.load_users(self.role_filter.currentText())
            else:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to {status_text} user account"
                )

    def delete_user(self, user_id):
        user = execute_query("SELECT username, role FROM users WHERE user_id = %s", (user_id,))
        if not user:
            return

        if user[0]['username'] == 'admin' or user[0]['role'] == 'admin':
            QMessageBox.warning(self, "Cannot Delete", "The main admin account cannot be deleted.")
            return

        confirm = QMessageBox.question(self, "Confirm Deletion",
                                      f"Are you sure you want to delete user '{user[0]['username']}'? This action cannot be undone and will delete all their bookings.",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            success = True
            try:
                # Delete user's bookings first (due to CASCADE on user_id in bookings table)
                # No need for explicit delete on 'customers', 'restaurants', 'delivery_personnel'
                # as those tables are gone or conceptually merged into users table.
                # If specific foreign key relationships exist, they should be defined with ON DELETE CASCADE.
                
                # Delete the user itself (this should cascade delete related bookings if setup correctly)
                result = execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), fetch=False)
                if result is None:
                    success = False

                if success:
                    QMessageBox.information(self, "Success", f"User '{user[0]['username']}' and all associated data have been deleted successfully.")
                    self.load_users(self.role_filter.currentText()) # Refresh the users list
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete user. There may be associated data that couldn't be deleted.")
            except Exception as e:
                print(f"Error deleting user: {e}")
                QMessageBox.critical(self, "Error", f"An error occurred while deleting the user: {str(e)}")

    # --- Booking Management Page (Replaces Orders Management) ---
    def create_bookings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Booking Management")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.booking_search_input = QLineEdit()
        self.booking_search_input.setPlaceholderText("Search by user, facility name or booking number")
        self.booking_search_input.setFixedWidth(150)

        date_label = QLabel("Date:")

        self.start_date_booking = QDateEdit()
        self.start_date_booking.setCalendarPopup(True)
        self.start_date_booking.setDisplayFormat("yyyy-MM-dd")  # Enforce input format
        self.start_date_booking.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_booking.setStyleSheet(self.styleSheet())

        to_label = QLabel("to")

        self.end_date_booking = QDateEdit()
        self.end_date_booking.setCalendarPopup(True)
        self.end_date_booking.setDisplayFormat("yyyy-MM-dd")  # Enforce input format
        self.end_date_booking.setDate(QDate.currentDate().addMonths(1))
        self.end_date_booking.setStyleSheet(self.styleSheet())

        self.start_date_booking.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: black;  /* Make input text black */
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)

        self.end_date_booking.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: black;  /* Make input text black */
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)

        status_label = QLabel("Status:")
        self.booking_status_filter = QComboBox()
        self.booking_status_filter.addItems([
            "All Status", "Confirmed", "Pending Approval", "Completed", "Cancelled"
        ])

        self.booking_status_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: #2c3e50;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView {
                background-color: #3498db;  /* Blue dropdown background */
                color: white;               /* White text */
                selection-background-color: #2980b9; /* Darker blue on selection */
                selection-color: white;
                }
            """)


        search_btn = QPushButton("Search")
        search_btn.setObjectName("action-button")
        search_btn.clicked.connect(self.search_bookings)

        refresh_bar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("action-button")
        refresh_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold;")
        refresh_btn.clicked.connect(lambda: self.load_bookings(True))
        last_refresh_label = QLabel("Auto-refreshes periodically") # Removed hardcoded 3 seconds
        last_refresh_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        refresh_bar.addWidget(refresh_btn)
        refresh_bar.addWidget(last_refresh_label)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.booking_search_input, 3)
        search_layout.addWidget(date_label)
        search_layout.addWidget(self.start_date_booking)
        search_layout.addWidget(to_label)
        search_layout.addWidget(self.end_date_booking)
        search_layout.addWidget(status_label)
        search_layout.addWidget(self.booking_status_filter, 2)
        search_layout.addWidget(search_btn)
        search_layout.addLayout(refresh_bar)

        self.bookings_table = QTableWidget()
        self.bookings_table.setColumnCount(7)
        self.bookings_table.setHorizontalHeaderLabels([
            "Booking #", "User", "Facility", "Building", "Time Slot", "Status", "Actions"
        ])
        self.bookings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bookings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bookings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bookings_table.setAlternatingRowColors(True)
        self.bookings_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")
        layout.addWidget(header)
        layout.addLayout(search_layout)
        layout.addWidget(self.bookings_table)

        return page

    def search_bookings(self):
        search_term = self.booking_search_input.text().strip()
        start_date = self.start_date_booking.date().toString("yyyy-MM-dd")
        end_date = self.end_date_booking.date().toString("yyyy-MM-dd")
        status = self.booking_status_filter.currentText()

        if status == "All Status":
            status = None

        self.load_bookings(force_refresh=True, search_term=search_term, start_date=start_date, end_date=end_date, status=status)

    def load_bookings(self, force_refresh=False, search_term=None, start_date=None, end_date=None, status=None):
        try:
            # Reusing search_bookings from db_utils (which replaced search_orders)
            from db_utils import get_user_bookings # Renamed for clarity, it takes user_id, status, dates
            
            # For admin, we want all bookings, so no user_id filter needed initially.
            # We'll adapt search_bookings to handle general search.
            # (Assuming get_user_bookings in db_utils can be adapted or a new function created for admin)
            
            # For simplicity, let's craft the query directly here for admin view.
            query = """
                SELECT bk.*, u.username as user_name, f.name as facility_name, bu.name as building_name
                FROM bookings bk
                JOIN users u ON bk.user_id = u.user_id
                JOIN facilities f ON bk.facility_id = f.facility_id
                JOIN buildings bu ON f.building_id = bu.building_id
                WHERE 1=1
            """
            params = []

            if search_term:
                query += " AND (u.username LIKE %s OR f.name LIKE %s OR bk.booking_number LIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])

            if status:
                query += " AND bk.status = %s"
                params.append(status)

            if start_date:
                query += " AND bk.start_time >= %s"
                params.append(f"{start_date} 00:00:00")

            if end_date:
                query += " AND bk.end_time <= %s"
                params.append(f"{end_date} 23:59:59") # Include entire end day

            query += " ORDER BY bk.start_time DESC"

            bookings = execute_query(query, params)

            if not bookings:
                self.display_no_data_message(self.bookings_table, "No bookings found matching the criteria.")
                return

            current_booking_ids = {}
            for row in range(self.bookings_table.rowCount()):
                booking_num_item = self.bookings_table.item(row, 0)
                if booking_num_item:
                    current_booking_ids[booking_num_item.text()] = row

            for booking in bookings:
                booking_num = booking.get('booking_number', f"N/A-{booking['booking_id']}")
                row = current_booking_ids.pop(booking_num, None) # Use pop to remove processed items
                if row is None:
                    row = self.bookings_table.rowCount()
                    self.bookings_table.insertRow(row)

                self.bookings_table.setItem(row, 0, QTableWidgetItem(booking_num))
                self.bookings_table.setItem(row, 1, QTableWidgetItem(booking['user_name']))
                self.bookings_table.setItem(row, 2, QTableWidgetItem(booking['facility_name']))
                self.bookings_table.setItem(row, 3, QTableWidgetItem(booking['building_name']))

                time_slot = f"{booking['start_time'].strftime('%Y-%m-%d %H:%M')} - {booking['end_time'].strftime('%H:%M')}"
                self.bookings_table.setItem(row, 4, QTableWidgetItem(time_slot))

                status_item = QTableWidgetItem(booking['status'])
                # Set color based on status
                if booking['status'] == 'Confirmed':
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                elif booking['status'] == 'Cancelled':
                    status_item.setForeground(Qt.GlobalColor.red)
                elif booking['status'] == 'Pending Approval':
                    status_item.setForeground(Qt.GlobalColor.darkYellow)
                elif booking['status'] == 'Completed':
                    status_item.setForeground(Qt.GlobalColor.blue)
                self.bookings_table.setItem(row, 5, status_item)

                # Actions - view/manage button
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(5)

                # View button
                view_btn = QPushButton("View")
                view_btn.setObjectName("action-button")
                view_btn.clicked.connect(partial(self.view_booking_details, booking['booking_id']))
                actions_layout.addWidget(view_btn)

                # Dropdown (only for editable statuses)
                editable_statuses = ["Pending Approval", "Confirmed"]
                if booking['status'] in editable_statuses:
                    status_combo = QComboBox()
                    status_combo.addItem("Change Status")
                    if booking['status'] == "Pending Approval":
                        status_combo.addItem("Approve")
                    status_combo.addItem("Cancel")
                    status_combo.addItem("Mark Completed")

                    status_combo.currentIndexChanged.connect(
                        partial(self.handle_booking_status_change, booking['booking_id'], status_combo)
                    )
                    actions_layout.addWidget(status_combo)
                    status_combo.setStyleSheet("""
                        QComboBox {
                            background-color: yellow;
                            color: black;
                            padding: 4px;
                            border-radius: 4px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            selection-background-color: #3498db;
                            selection-color: white;
                        }
                    """)

                # Apply layout
                actions_widget.setLayout(actions_layout)
                actions_widget.setMinimumHeight(40)
                self.bookings_table.setCellWidget(row, 6, actions_widget)


            # Remove any rows that are no longer in the query results
            rows_to_remove = sorted(current_booking_ids.values(), reverse=True)
            for row in rows_to_remove:
                self.bookings_table.removeRow(row)

        except Exception as e:
            error_msg = f"Failed to load bookings: {str(e)}"
            if force_refresh:
                print(error_msg)
            self.display_db_error_message(self.bookings_table, error_msg)

    def view_booking_details(self, booking_id):
        try:
            booking = execute_query("""
                SELECT bk.*, u.username as user_name, u.email as user_email, u.role as user_role,
                       f.name as facility_name, f.type as facility_type, f.capacity,
                       b.name as building_name, b.address as building_address
                FROM bookings bk
                JOIN users u ON bk.user_id = u.user_id
                JOIN facilities f ON bk.facility_id = f.facility_id
                JOIN buildings b ON f.building_id = b.building_id
                WHERE bk.booking_id = %s
            """, (booking_id,))

            if not booking:
                QMessageBox.warning(self, "Error", f"Booking #{booking_id} not found.")
                return

            booking = booking[0]
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Booking {booking['booking_number']} Details")
            dialog.setMinimumWidth(600)
            dialog.setStyleSheet("""
                QDialog { background-color: #2c3e50; color: white; }
                QLabel { color: white; font-size: 12px; }
                QGroupBox { color: white; border: 1px solid #7f8c8d; border-radius: 4px; margin-top: 10px; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
                QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
                QPushButton:hover { background-color: #2980b9; }
            """)
            layout = QVBoxLayout(dialog)

            header_label = QLabel(f"Booking {booking['booking_number']}")
            header_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            layout.addWidget(header_label)

            status_layout = QHBoxLayout()
            status_label = QLabel("Status:")
            status_value = QLabel(booking['status'])
            status_color = "white"
            if booking['status'] == 'Confirmed': status_color = "#2ecc71"
            elif booking['status'] == 'Cancelled': status_color = "#e74c3c"
            elif booking['status'] == 'Pending Approval': status_color = "#f39c12"
            elif booking['status'] == 'Completed': status_color = "#3498db"
            status_value.setStyleSheet(f"color: {status_color}; font-weight: bold;")
            status_layout.addWidget(status_label)
            status_layout.addWidget(status_value)
            status_layout.addStretch()
            layout.addLayout(status_layout)

            layout.addWidget(QLabel(f"Purpose: {booking['purpose']}"))
            layout.addWidget(QLabel(f"Time: {booking['start_time'].strftime('%Y-%m-%d %H:%M')} to {booking['end_time'].strftime('%H:%M')}"))

            user_group = QGroupBox("Booked By")
            user_layout = QFormLayout(user_group)
            user_layout.addRow("Username:", QLabel(booking['user_name']))
            user_layout.addRow("Email:", QLabel(booking['user_email']))
            user_layout.addRow("Role:", QLabel(booking['user_role'].capitalize()))
            layout.addWidget(user_group)

            facility_group = QGroupBox("Facility Details")
            facility_layout = QFormLayout(facility_group)
            facility_layout.addRow("Facility Name:", QLabel(booking['facility_name']))
            facility_layout.addRow("Type:", QLabel(booking['facility_type']))
            facility_layout.addRow("Capacity:", QLabel(str(booking['capacity'])))
            facility_layout.addRow("Building:", QLabel(booking['building_name']))
            facility_layout.addRow("Building Address:", QLabel(booking['building_address']))
            layout.addWidget(facility_group)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load booking details: {str(e)}")
            print(f"Error loading booking details: {e}")

    def handle_booking_status_change(self, booking_id, new_status_text, combo_box):
        """Handle status change from dropdown in bookings table."""
        if new_status_text == "Change Status": # Default item, no action
            return

        db_status = new_status_text.replace(" ", "") # Remove spaces for enum

        reply = QMessageBox.question(
            self, "Confirm Status Change",
            f"Are you sure you want to change booking status to '{new_status_text}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Update booking status in DB
                query = "UPDATE bookings SET status = %s WHERE booking_id = %s"
                result = execute_query(query, (db_status, booking_id), fetch=False)

                if result is not None:
                    QMessageBox.information(self, "Success", f"Booking #{booking_id} status updated to {new_status_text}.")
                    self.load_bookings() # Refresh table
                else:
                    QMessageBox.critical(self, "Error", "Failed to update booking status.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update booking status: {str(e)}")
        else:
            # If user cancels, reset combo box to original state (or 'Change Status')
            combo_box.setCurrentIndex(0) # Reset to "Change Status"

    # --- Reports Page (Updated for SCNFBS) ---
    def create_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(15)

        header = QLabel("Reports & Analytics")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #ecf0f1; background-color: #2c3e50; padding: 10px; border-radius: 4px;")

        date_range_layout = QHBoxLayout()
        date_range_label = QLabel("Date Range:")
        date_range_label.setStyleSheet("color: #2c3e50;")
        self.reports_start_date = QDateEdit() # Renamed to avoid conflict
        self.reports_start_date.setCalendarPopup(True)
        self.reports_start_date.setDate(QDate.currentDate().addDays(-30))
        self.reports_end_date = QDateEdit() # Renamed to avoid conflict
        self.reports_end_date.setCalendarPopup(True)
        self.reports_end_date.setDate(QDate.currentDate())

        date_style = """
            QDateEdit { background-color: #34495e; color: white; border: 1px solid #3498db; border-radius: 4px; padding: 5px; }
            QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 20px; border-left: 1px solid #3498db; }
            QCalendarWidget QWidget { background-color: #34495e; }
            QCalendarWidget QToolButton { color: white; background-color: #2c3e50; border: 1px solid #3498db; border-radius: 4px; padding: 5px; }
            QCalendarWidget QMenu { color: white; background-color: #2c3e50; }
            QCalendarWidget QSpinBox { color: white; background-color: #2c3e50; selection-background-color: #3498db; selection-color: white; }
            QCalendarWidget QAbstractItemView:enabled { color: white; background-color: #2c3e50; selection-background-color: #3498db; selection-color: white; }
            QCalendarWidget QAbstractItemView:disabled { color: #7f8c8d; }
        """
        self.reports_start_date.setStyleSheet(date_style)
        self.reports_end_date.setStyleSheet(date_style)

        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setObjectName("action-button")
        refresh_btn.clicked.connect(self.refresh_analytics)

        date_range_layout.addWidget(date_range_label)
        date_range_layout.addWidget(self.reports_start_date)
        date_range_layout.addWidget(QLabel("to"))
        date_range_layout.addWidget(self.reports_end_date)
        date_range_layout.addStretch()
        date_range_layout.addWidget(refresh_btn)

        # Key metrics cards - Updated for SCNFBS
        metrics_layout = QHBoxLayout()

        total_bookings_card = QFrame()
        total_bookings_card.setObjectName("metric-card")
        total_bookings_layout = QVBoxLayout(total_bookings_card)
        self.total_bookings_label = QLabel("0")
        self.total_bookings_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        total_bookings_layout.addWidget(QLabel("Total Bookings"))
        total_bookings_layout.addWidget(self.total_bookings_label)

        total_hours_card = QFrame()
        total_hours_card.setObjectName("metric-card")
        total_hours_layout = QVBoxLayout(total_hours_card)
        self.total_hours_label = QLabel("0.0 hrs")
        self.total_hours_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        total_hours_layout.addWidget(QLabel("Total Booked Hours"))
        total_hours_layout.addWidget(self.total_hours_label)

        avg_duration_card = QFrame()
        avg_duration_card.setObjectName("metric-card")
        avg_duration_layout = QVBoxLayout(avg_duration_card)
        self.avg_duration_label = QLabel("0 min")
        self.avg_duration_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        avg_duration_layout.addWidget(QLabel("Avg. Booking Duration"))
        avg_duration_layout.addWidget(self.avg_duration_label)
        
        # New: Facility Utilization Rate
        utilization_card = QFrame()
        utilization_card.setObjectName("metric-card")
        utilization_layout = QVBoxLayout(utilization_card)
        self.utilization_label = QLabel("0.0%")
        self.utilization_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        utilization_layout.addWidget(QLabel("Avg. Utilization Rate"))
        utilization_layout.addWidget(self.utilization_label)


        metrics_layout.addWidget(total_bookings_card)
        metrics_layout.addWidget(total_hours_card)
        metrics_layout.addWidget(avg_duration_card)
        metrics_layout.addWidget(utilization_card)


        # Charts section - Updated for SCNFBS
        charts_layout = QHBoxLayout()

        # Bookings by Status Chart
        status_chart_card = QFrame()
        status_chart_card.setObjectName("chart-card")
        status_chart_layout = QVBoxLayout(status_chart_card)
        status_chart_layout.addWidget(QLabel("Bookings by Status"))
        
        self.status_chart = QFrame()
        self.status_chart.setMinimumHeight(300)
        chart_layout = QVBoxLayout(self.status_chart)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        status_chart_layout.addWidget(self.status_chart)

        # Booking Trend Chart (by day)
        booking_trend_card = QFrame()
        booking_trend_card.setObjectName("chart-card")
        booking_trend_layout = QVBoxLayout(booking_trend_card)
        booking_trend_layout.addWidget(QLabel("Daily Booking Trend"))

        self.booking_trend_chart = QFrame()
        self.booking_trend_chart.setMinimumHeight(300)
        chart_layout = QVBoxLayout(self.booking_trend_chart)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        booking_trend_layout.addWidget(self.booking_trend_chart)

        charts_layout.addWidget(status_chart_card)
        charts_layout.addWidget(booking_trend_card)

        # Detailed Reports Section - Updated for SCNFBS
        reports_tabs = QTabWidget()
        reports_tabs.setMinimumHeight(300)

        # Top Facilities Tab
        facilities_tab = QWidget()
        facilities_layout = QVBoxLayout(facilities_tab)
        self.top_facilities_table = QTableWidget()
        self.top_facilities_table.setColumnCount(5)
        self.top_facilities_table.setHorizontalHeaderLabels(["Facility Name", "Building", "Type", "Total Bookings", "Total Hours"])
        self.top_facilities_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        facilities_layout.addWidget(self.top_facilities_table)
        
        # User Activity Tab
        user_activity_tab = QWidget()
        user_activity_layout = QVBoxLayout(user_activity_tab)
        self.user_activity_table = QTableWidget()
        self.user_activity_table.setColumnCount(4)
        self.user_activity_table.setHorizontalHeaderLabels(["Username", "Role", "Total Bookings", "Total Hours Booked"])
        self.user_activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        user_activity_layout.addWidget(self.user_activity_table)

        reports_tabs.addTab(facilities_tab, "Top Facilities")
        reports_tabs.addTab(user_activity_tab, "User Activity")

        scroll_layout.addWidget(header)
        scroll_layout.addLayout(date_range_layout)
        scroll_layout.addLayout(metrics_layout)
        scroll_layout.addLayout(charts_layout)
        scroll_layout.addWidget(reports_tabs)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        page.setStyleSheet("""
            QFrame#metric-card { background-color: #34495e; border-radius: 8px; padding: 15px; min-width: 200px; }
            QFrame#chart-card { background-color: #34495e; border-radius: 8px; padding: 15px; min-width: 400px; }
            QLabel { color: white; }
            QTableWidget { background-color: #34495e; color: white; gridline-color: #7f8c8d; alternate-background-color: #2c3e50; }
            QHeaderView::section { background-color: #2c3e50; color: white; padding: 5px; border: none; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #7f8c8d; background-color: #34495e; }
            QTabBar::tab { background-color: #2c3e50; color: white; padding: 8px 15px; border: 1px solid #7f8c8d; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #34495e; }
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background-color: #2c3e50; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background-color: #3498db; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.refresh_analytics()
        return page

    def refresh_analytics(self):
        start_date = self.reports_start_date.date().toString("yyyy-MM-dd")
        end_date_obj = self.reports_end_date.date().addDays(1)
        end_date = end_date_obj.toString("yyyy-MM-dd")

        try:
            # Get key metrics
            metrics_query = """
                SELECT
                    COUNT(*) as total_bookings,
                    SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60 as total_booked_hours,
                    AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)) as avg_booking_duration_minutes
                FROM bookings
                WHERE start_time BETWEEN %s AND %s AND status = 'Confirmed'
            """
            metrics = execute_query(metrics_query, (start_date, end_date))

            if metrics and metrics[0]:
                self.total_bookings_label.setText(str(metrics[0]['total_bookings'] or 0))
                self.total_hours_label.setText(f"{float(metrics[0]['total_booked_hours'] or 0):.1f} hrs")
                self.avg_duration_label.setText(f"{int(metrics[0]['avg_booking_duration_minutes'] or 0)} min")
            
            # Calculate average utilization rate (needs more complex logic, simplified for now)
            # This requires total available hours for all facilities within the date range
            # For a basic approximation, let's assume maximum possible is a fixed number of facilities * hours/day * days
            
            # Simplified utilization: Sum of booked hours / (Number of bookable facilities * total hours in period)
            try:
                bookable_facilities_count = execute_query("SELECT COUNT(*) as count FROM facilities WHERE is_bookable = TRUE")
                bookable_facilities_count = bookable_facilities_count[0]['count'] if bookable_facilities_count else 0
                
                # Calculate total available hours in the period for all bookable facilities
                # Assuming 12 hours/day for each facility for simplicity (e.g., 8 AM - 8 PM)
                time_diff_days = (self.reports_end_date.date().toPython() - self.reports_start_date.date().toPython()).days + 1
                total_available_hours_in_period = bookable_facilities_count * time_diff_days * 12 # 12 hours per day
                
                if total_available_hours_in_period > 0 and metrics[0]['total_booked_hours'] is not None:
                    utilization_rate = (metrics[0]['total_booked_hours'] / total_available_hours_in_period) * 100
                    self.utilization_label.setText(f"{utilization_rate:.1f}%")
                else:
                    self.utilization_label.setText("0.0%")
            except Exception as e:
                print(f"Error calculating utilization: {e}")
                self.utilization_label.setText("N/A")

            # Get bookings by status
            status_query = """
                SELECT status, COUNT(*) as count
                FROM bookings
                WHERE start_time BETWEEN %s AND %s
                GROUP BY status
            """
            status_data = execute_query(status_query, (start_date, end_date))

            # Get booking trend
            booking_trend_query = """
                SELECT DATE(start_time) as date, COUNT(*) as count
                FROM bookings
                WHERE start_time BETWEEN %s AND %s AND status = 'Confirmed'
                GROUP BY DATE(start_time)
                ORDER BY date
            """
            booking_trend_data = execute_query(booking_trend_query, (start_date, end_date))

            # Clear previous charts
            for i in reversed(range(self.status_chart.layout().count())):
                widget = self.status_chart.layout().itemAt(i).widget()
                if widget: widget.setParent(None)

            for i in reversed(range(self.booking_trend_chart.layout().count())):
                widget = self.booking_trend_chart.layout().itemAt(i).widget()
                if widget: widget.setParent(None)

            # Create status pie chart
            if status_data:
                status_fig = Figure(figsize=(5, 4), dpi=100)
                status_canvas = FigureCanvas(status_fig)
                ax = status_fig.add_subplot(111)

                labels = [item['status'] for item in status_data]
                sizes = [item['count'] for item in status_data]

                colors = plt.cm.Paired(np.arange(len(labels))/len(labels))

                ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                      startangle=90, colors=colors)
                ax.axis('equal')
                self.status_chart.layout().addWidget(status_canvas)
                status_fig.tight_layout()
                status_canvas.draw()

            # Create booking trend chart
            if booking_trend_data:
                booking_trend_fig = Figure(figsize=(5, 4), dpi=100)
                booking_trend_canvas = FigureCanvas(booking_trend_fig)
                ax = booking_trend_fig.add_subplot(111)

                dates = [item['date'] for item in booking_trend_data]
                counts = [item['count'] for item in booking_trend_data]

                ax.plot(dates, counts, 'o-', color='#3498db', linewidth=2)
                ax.set_title('Daily Confirmed Bookings')
                ax.set_ylabel('Number of Bookings')
                ax.grid(True, linestyle='--', alpha=0.7)

                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

                self.booking_trend_chart.layout().addWidget(booking_trend_canvas)
                booking_trend_fig.tight_layout()
                booking_trend_canvas.draw()

            # Get top facilities (by total hours booked)
            facilities_query = """
                SELECT
                    f.name,
                    b.name as building_name,
                    f.type,
                    COUNT(bk.booking_id) as total_bookings,
                    SUM(TIMESTAMPDIFF(MINUTE, bk.start_time, bk.end_time)) / 60 as total_hours
                FROM facilities f
                JOIN buildings b ON f.building_id = b.building_id
                LEFT JOIN bookings bk ON f.facility_id = bk.facility_id
                WHERE bk.start_time BETWEEN %s AND %s AND bk.status = 'Confirmed'
                GROUP BY f.facility_id, f.name, b.name, f.type
                ORDER BY total_hours DESC
                LIMIT 10
            """
            facilities_data = execute_query(facilities_query, (start_date, end_date))

            if facilities_data:
                self.top_facilities_table.setRowCount(len(facilities_data))
                for i, facility in enumerate(facilities_data):
                    self.top_facilities_table.setItem(i, 0, QTableWidgetItem(facility['name']))
                    self.top_facilities_table.setItem(i, 1, QTableWidgetItem(facility['building_name']))
                    self.top_facilities_table.setItem(i, 2, QTableWidgetItem(facility['type']))
                    self.top_facilities_table.setItem(i, 3, QTableWidgetItem(str(facility['total_bookings'])))
                    self.top_facilities_table.setItem(i, 4, QTableWidgetItem(f"{float(facility['total_hours'] or 0):.1f} hrs"))

            # Get user activity (by total hours booked)
            user_activity_query = """
                SELECT
                    u.username,
                    u.role,
                    COUNT(bk.booking_id) as total_bookings,
                    SUM(TIMESTAMPDIFF(MINUTE, bk.start_time, bk.end_time)) / 60 as total_hours_booked
                FROM users u
                JOIN bookings bk ON u.user_id = bk.user_id
                WHERE bk.start_time BETWEEN %s AND %s AND bk.status = 'Confirmed'
                GROUP BY u.user_id, u.username, u.role
                ORDER BY total_hours_booked DESC
                LIMIT 10
            """
            user_activity_data = execute_query(user_activity_query, (start_date, end_date))

            if user_activity_data:
                self.user_activity_table.setRowCount(len(user_activity_data))
                for i, user_act in enumerate(user_activity_data):
                    self.user_activity_table.setItem(i, 0, QTableWidgetItem(user_act['username']))
                    self.user_activity_table.setItem(i, 1, QTableWidgetItem(user_act['role'].capitalize()))
                    self.user_activity_table.setItem(i, 2, QTableWidgetItem(str(user_act['total_bookings'])))
                    self.user_activity_table.setItem(i, 3, QTableWidgetItem(f"{float(user_act['total_hours_booked'] or 0):.1f} hrs"))

        except Exception as e:
            print(f"Error refreshing analytics: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load analytics data: {str(e)}")

    # --- System Settings Page (Adjusted for SCNFBS) ---
    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("System Settings")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #ecf0f1; background-color: #2c3e50; padding: 10px; border-radius: 4px; margin-bottom: 15px;")

        tabs = QTabWidget()

        # 1. General Settings Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        app_group = QGroupBox("Application Settings")
        app_group.setStyleSheet("QGroupBox { color: white; border: 1px solid #3498db; border-radius: 5px; margin-top: 15px; padding-top: 10px; }")
        app_layout = QFormLayout(app_group)

        self.app_name_input = QLineEdit("Smart Campus System") # Changed default
        app_layout.addRow("Application Name:", self.app_name_input)

        self.currency_selector = QComboBox()
        self.currency_selector.addItems(["AED", "USD", "EUR", "GBP", "CNY"])
        self.currency_selector.setCurrentText("AED")
        app_layout.addRow("Default Currency:", self.currency_selector)

        self.timezone_selector = QComboBox()
        self.timezone_selector.addItems(["UTC", "UTC+4 (UAE)", "UTC+3 (KSA)", "UTC+1 (CET)", "UTC-5 (EST)"])
        self.timezone_selector.setCurrentText("UTC+4 (UAE)")
        app_layout.addRow("Default Timezone:", self.timezone_selector)

        general_layout.addWidget(app_group)
        
        # 2. Booking Rules Management (New Section)
        booking_rules_group = QGroupBox("Booking Rules Management")
        booking_rules_group.setStyleSheet("QGroupBox { color: white; border: 1px solid #3498db; border-radius: 5px; margin-top: 15px; padding-top: 10px; }")
        booking_rules_layout = QVBoxLayout(booking_rules_group)

        self.booking_rules_table = QTableWidget()
        self.booking_rules_table.setColumnCount(6)
        self.booking_rules_table.setHorizontalHeaderLabels(["Facility Type", "Max Duration (min)", "Min Advance (hrs)", "Max Concurrent", "Recurring", "Eligible Roles", "Actions"])
        self.booking_rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        booking_rules_layout.addWidget(self.booking_rules_table)
        
        add_rule_btn = QPushButton("Add/Edit Booking Rule")
        add_rule_btn.setObjectName("action-button")
        add_rule_btn.clicked.connect(self.add_edit_booking_rule)
        booking_rules_layout.addWidget(add_rule_btn)

        general_layout.addWidget(booking_rules_group)
        general_layout.addStretch()

        # Removed 'Order Settings' Tab (Business Rules, Order Processing, etc.)

        # 2. Database Backup Tab (Kept largely similar)
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)

        backup_group = QGroupBox("Database Backup")
        backup_group.setStyleSheet("QGroupBox { color: white; border: 1px solid #3498db; border-radius: 5px; margin-top: 15px; padding-top: 10px; }")
        backup_inner_layout = QVBoxLayout(backup_group)

        backup_form = QFormLayout()
        self.backup_path_input = QLineEdit("backups/")

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.backup_path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_backup_path)
        browse_btn.setMaximumWidth(80)
        path_layout.addWidget(browse_btn)

        backup_form.addRow("Backup Directory:", path_layout)

        self.auto_backup_checkbox = QCheckBox()
        self.auto_backup_checkbox.setChecked(True)
        backup_form.addRow("Enable Automatic Backups:", self.auto_backup_checkbox)

        self.backup_freq_combo = QComboBox()
        self.backup_freq_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.backup_freq_combo.setCurrentText("Daily")
        backup_form.addRow("Backup Frequency:", self.backup_freq_combo)

        backup_inner_layout.addLayout(backup_form)

        backup_buttons = QHBoxLayout()
        backup_now_btn = QPushButton("Backup Now")
        backup_now_btn.clicked.connect(self.backup_database)
        restore_btn = QPushButton("Restore from Backup")
        restore_btn.clicked.connect(self.restore_database)

        backup_buttons.addWidget(backup_now_btn)
        backup_buttons.addWidget(restore_btn)
        backup_inner_layout.addLayout(backup_buttons)

        utils_group = QGroupBox("Database Utilities")
        utils_group.setStyleSheet("QGroupBox { color: white; border: 1px solid #3498db; border-radius: 5px; margin-top: 15px; padding-top: 10px; }")
        utils_layout = QVBoxLayout(utils_group)

        utils_buttons = QHBoxLayout()
        optimize_btn = QPushButton("Optimize Database")
        optimize_btn.clicked.connect(self.optimize_database)
        clear_cache_btn = QPushButton("Clear System Cache")
        clear_cache_btn.clicked.connect(self.clear_system_cache)

        utils_buttons.addWidget(optimize_btn)
        utils_buttons.addWidget(clear_cache_btn)
        utils_layout.addLayout(utils_buttons)

        backup_layout.addWidget(backup_group)
        backup_layout.addWidget(utils_group)
        backup_layout.addStretch()

        tabs.addTab(general_tab, "General")
        tabs.addTab(backup_tab, "Backup & Maintenance")

        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_settings)

        button_layout.addStretch()
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(save_btn)

        layout.addWidget(header)
        layout.addWidget(tabs)
        layout.addLayout(button_layout)

        page.setStyleSheet("""
            QWidget { background-color: #34495e; color: white; }
            QTabWidget::pane { border: 1px solid #3498db; background-color: #34495e; border-radius: 5px; }
            QTabBar::tab { background-color: #2c3e50; color: white; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #3498db; }
            QLineEdit, QComboBox { background-color: #2c3e50; color: white; border: 1px solid #7f8c8d; border-radius: 4px; padding: 5px; min-height: 25px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; }
            QCheckBox { color: white; spacing: 5px; }
            QCheckBox::indicator { width: 15px; height: 15px; }
            QPushButton { background-color: #3498db; color: white; min-width: 120px; padding: 8px 15px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.load_booking_rules() # Load rules when page is created
        return page

    def load_booking_rules(self):
        self.booking_rules_table.setRowCount(0)
        try:
            rules = execute_query("SELECT * FROM booking_rules ORDER BY facility_type")
            if not rules:
                self.display_no_data_message(self.booking_rules_table, "No booking rules defined.")
                return
            
            self.booking_rules_table.setRowCount(len(rules))
            for row_idx, rule in enumerate(rules):
                self.booking_rules_table.setItem(row_idx, 0, QTableWidgetItem(rule['facility_type']))
                self.booking_rules_table.setItem(row_idx, 1, QTableWidgetItem(str(rule['max_booking_duration_minutes'])))
                self.booking_rules_table.setItem(row_idx, 2, QTableWidgetItem(str(rule['min_booking_advance_hours'])))
                self.booking_rules_table.setItem(row_idx, 3, QTableWidgetItem(str(rule['max_concurrent_bookings_per_user'])))
                self.booking_rules_table.setItem(row_idx, 4, QTableWidgetItem("Yes" if rule['can_recur'] else "No"))
                self.booking_rules_table.setItem(row_idx, 5, QTableWidgetItem(rule['applies_to_roles']))

                buttons_widget = QWidget()
                buttons_layout = QHBoxLayout(buttons_widget)
                buttons_layout.setContentsMargins(0, 0, 0, 0)
                buttons_layout.setSpacing(5)

                edit_btn = QPushButton("Edit")
                edit_btn.setObjectName("action-button")
                edit_btn.clicked.connect(lambda checked, r=rule: self.add_edit_booking_rule(r))

                delete_btn = QPushButton("Delete")
                delete_btn.setObjectName("delete-button")
                delete_btn.clicked.connect(lambda checked, rid=rule['rule_id']: self.delete_booking_rule(rid))

                buttons_layout.addWidget(edit_btn)
                buttons_layout.addWidget(delete_btn)
                self.booking_rules_table.setCellWidget(row_idx, 6, buttons_widget)

        except Exception as e:
            print(f"Error loading booking rules: {e}")
            self.display_db_error_message(self.booking_rules_table, "Failed to load booking rules.")

    def add_edit_booking_rule(self, rule=None):
        dialog = BookingRuleDialog(self, rule)
        if dialog.exec():
            self.load_booking_rules()

    def delete_booking_rule(self, rule_id):
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this booking rule?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = execute_query("DELETE FROM booking_rules WHERE rule_id = %s", (rule_id,), fetch=False)
                if result is not None:
                    QMessageBox.information(self, "Success", "Booking rule deleted successfully.")
                    self.load_booking_rules()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete booking rule.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


    def browse_backup_path(self):
        """Open a file dialog to select backup directory"""
        from PySide6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory",
            self.backup_path_input.text()
        )
        if directory:
            self.backup_path_input.setText(directory)

    def optimize_database(self):
        from db_utils import execute_query
        try:
            progress_msg = QMessageBox(self)
            progress_msg.setIcon(QMessageBox.Icon.Information)
            progress_msg.setWindowTitle("Database Optimization")
            progress_msg.setText("Optimizing database tables. Please wait...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_msg.show()

            tables = execute_query("SHOW TABLES")
            if not tables:
                progress_msg.close()
                QMessageBox.critical(self, "Optimization Failed", "Could not retrieve database tables.")
                return

            for table_dict in tables:
                table_name = list(table_dict.values())[0]
                execute_query(f"OPTIMIZE TABLE {table_name}", fetch=False)

            progress_msg.close()
            QMessageBox.information(self, "Optimization Complete", "Database tables have been optimized successfully.")

        except Exception as e:
            if 'progress_msg' in locals():
                progress_msg.close()
            QMessageBox.critical(self, "Optimization Failed", f"Failed to optimize database: {str(e)}")

    def clear_system_cache(self):
        import shutil
        import tempfile
        import os

        reply = QMessageBox.question(
            self, "Clear Cache",
            "This will clear all temporary files and cached data.\nDo you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            progress_msg = QMessageBox(self)
            progress_msg.setIcon(QMessageBox.Icon.Information)
            progress_msg.setWindowTitle("Clearing Cache")
            progress_msg.setText("Clearing system cache. Please wait...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_msg.show()

            # Updated cache directory name
            temp_dir = os.path.join(tempfile.gettempdir(), "campus_system_cache")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                os.makedirs(temp_dir, exist_ok=True)

            progress_msg.close()
            QMessageBox.information(self, "Cache Cleared", "System cache has been cleared successfully.")

        except Exception as e:
            if 'progress_msg' in locals():
                progress_msg.close()
            QMessageBox.critical(self, "Operation Failed", f"Failed to clear cache: {str(e)}")

    def save_settings(self):
        import json
        import os

        settings = {
            "app_name": self.app_name_input.text(),
            "currency": self.currency_selector.currentText(),
            "timezone": self.timezone_selector.currentText(),
            # Removed food delivery specific settings
            "backup_path": self.backup_path_input.text(),
            "auto_backup": self.auto_backup_checkbox.isChecked(),
            "backup_frequency": self.backup_freq_combo.currentText()
        }

        try:
            os.makedirs("settings", exist_ok=True)
            with open("settings/app_settings.json", "w") as f:
                json.dump(settings, f, indent=4)

            QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Settings Error", f"Failed to save settings: {str(e)}")

    def reset_settings(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_name_input.setText("Smart Campus System") # Changed default
            self.currency_selector.setCurrentText("AED")
            self.timezone_selector.setCurrentText("UTC+4 (UAE)")

            # Removed food delivery specific settings resets

            self.backup_path_input.setText("backups/")
            self.auto_backup_checkbox.setChecked(True)
            self.backup_freq_combo.setCurrentText("Daily")

            QMessageBox.information(self, "Reset Complete", "All settings have been reset to default values.")

    def backup_database(self):
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        import datetime
        from pathlib import Path
        import time

        start_time = time.time()
        print("\n==== DATABASE BACKUP STARTED ====")
        print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        backup_dir = Path(self.backup_path_input.text().strip())
        try:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Backup directory created/verified: {backup_dir}")
        except Exception as e:
            error_msg = f"Could not create backup directory: {str(e)}"
            print(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "Backup Failed", error_msg)
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Updated backup file name
        backup_file = backup_dir / f"campus_system_backup_{timestamp}.sql"
        print(f"Backup will be saved to: {backup_file}")

        db_host = os.environ.get('DB_HOST', 'localhost')
        db_user = os.environ.get('DB_USER', 'root')
        db_password = os.environ.get('DB_PASSWORD', '')
        # Updated DB_NAME
        db_name = os.environ.get('DB_NAME', 'campus_navigation_booking')
        print(f"Database connection details: host={db_host}, user={db_user}, database={db_name}")

        from db_utils import get_db_connection

        try:
            print("Attempting to connect to database...")
            connection = get_db_connection()
            if not connection:
                error_msg = "Could not connect to database for backup."
                print(f"ERROR: {error_msg}")
                QMessageBox.critical(self, "Backup Failed", error_msg)
                return

            print("Successfully connected to database")
            cursor = connection.cursor(dictionary=True)

            print("Getting list of tables...")
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
            table_count = len(tables)
            print(f"Found {table_count} tables to backup: {', '.join(tables)}")

            progress = QProgressDialog("Preparing to backup database...", "Cancel", 0, table_count, self)
            progress.setWindowTitle("Database Backup")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            print("Starting backup process...")
            with open(backup_file, 'w') as f:
                # Updated header
                f.write(f"-- Smart Campus System Database Backup\n")
                f.write(f"-- Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- Database: {db_name}\n\n")
                print("Wrote backup file header")

                for i, table in enumerate(tables):
                    progress.setValue(i)
                    progress.setLabelText(f"Backing up table: {table} ({i+1}/{table_count})")
                    if progress.wasCanceled():
                        print("Backup cancelled by user")
                        cursor.close()
                        connection.close()
                        if os.path.exists(backup_file): os.remove(backup_file)
                        return
                    QApplication.processEvents()

                    try:
                        print(f"Backing up table structure for '{table}'...")
                        cursor.execute(f"SHOW CREATE TABLE `{table}`")
                        create_table_sql = cursor.fetchone()['Create Table']

                        f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                        f.write(f"{create_table_sql};\n\n")

                        print(f"Fetching data for table '{table}'...")
                        cursor.execute(f"SELECT * FROM `{table}`")
                        rows = cursor.fetchall()
                        print(f"Found {len(rows)} rows in table '{table}'")

                        if rows:
                            columns = list(rows[0].keys())
                            batch_size = 100
                            total_rows = len(rows)

                            for batch_start in range(0, total_rows, batch_size):
                                if total_rows > 1000:
                                    progress.setLabelText(f"Backing up table: {table} - Rows {batch_start}/{total_rows}")
                                    QApplication.processEvents()
                                if progress.wasCanceled():
                                    print("Backup cancelled by user during data processing")
                                    cursor.close()
                                    connection.close()
                                    if os.path.exists(backup_file): os.remove(backup_file)
                                    return

                                batch = rows[batch_start:batch_start + batch_size]
                                values_list = []
                                for row in batch:
                                    row_values = []
                                    for column in columns:
                                        if row[column] is None:
                                            row_values.append("NULL")
                                        elif isinstance(row[column], (int, float)):
                                            row_values.append(str(row[column]))
                                        elif isinstance(row[column], bytes):
                                            hex_str = row[column].hex()
                                            row_values.append(f"0x{hex_str}")
                                        else:
                                            val = str(row[column]).replace("'", "''")
                                            row_values.append(f"'{val}'")
                                    values_list.append(f"({', '.join(row_values)})")

                                f.write(f"INSERT INTO `{table}` (`{'`, `'.join(columns)}`) VALUES\n")
                                f.write(",\n".join(values_list))
                                f.write(";\n\n")
                        else:
                            print(f"Table '{table}' is empty - no data to backup")
                    except Exception as table_error:
                        print(f"ERROR processing table '{table}': {str(table_error)}")
                        progress.close()
                        cursor.close()
                        connection.close()
                        if os.path.exists(backup_file): os.remove(backup_file)
                        QMessageBox.critical(self, "Backup Failed", f"Error while backing up table '{table}': {str(table_error)}")
                        return

                progress.setValue(table_count)
                print("Backup completed successfully")

            cursor.close()
            connection.close()
            print("Database connection closed")

            backup_size = os.path.getsize(backup_file)
            end_time = time.time()
            duration = end_time - start_time
            print(f"Backup took {duration:.2f} seconds")
            print("==== DATABASE BACKUP COMPLETED ====\n")

            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database backup completed successfully.\nBackup stored at: {backup_file}\nFile size: {backup_size/1024/1024:.2f} MB\nTime: {duration:.2f} seconds"
            )

        except Exception as e:
            print(f"CRITICAL ERROR during backup: {str(e)}")
            if 'progress' in locals(): progress.close()
            if 'cursor' in locals() and cursor: cursor.close()
            if 'connection' in locals() and connection and connection.is_connected():
                connection.close()
            if os.path.exists(backup_file):
                try: os.remove(backup_file)
                except Exception as rm_err: print(f"Warning: Could not remove incomplete backup file: {str(rm_err)}")
            print("==== DATABASE BACKUP FAILED ====\n")
            QMessageBox.critical(self, "Backup Failed", f"Failed to perform database backup: {str(e)}")

    def restore_database(self):
        from PySide6.QtWidgets import QFileDialog, QProgressDialog
        from PySide6.QtCore import Qt, QProcess
        import os
        import re
        import time
        import datetime
        import sys

        start_time = time.time()
        print("\n==== DATABASE RESTORE STARTED ====")
        print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        reply = QMessageBox.warning(
            self, "Restore Database",
            "WARNING: Restoring from backup will overwrite the current database. This action cannot be undone.\n\nDo you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            print("Restore cancelled by user at confirmation dialog")
            return

        backup_file, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", str(self.backup_path_input.text()), "SQL Files (*.sql)"
        )
        if not backup_file:
            print("Restore cancelled - no file selected")
            return

        try:
            file_size = os.path.getsize(backup_file)
            print(f"Backup file size: {file_size/1024/1024:.2f} MB")
        except Exception as e:
            print(f"Warning: Could not determine file size: {str(e)}")

        from db_utils import get_db_connection

        try:
            print("Reading backup file...")
            with open(backup_file, 'r') as f:
                sql_file = f.read()

            print("Splitting SQL file into statements...")
            statements = re.split(r';\s*\n', sql_file)
            total_statements = len([s for s in statements if s.strip()])
            print(f"Found {total_statements} SQL statements to execute")

            progress = QProgressDialog("Preparing to restore database...", "Cancel", 0, total_statements, self)
            progress.setWindowTitle("Database Restore")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            print("Attempting to connect to database...")
            connection = get_db_connection()
            if not connection:
                print("ERROR: Could not connect to database for restore")
                QMessageBox.critical(self, "Restore Failed", "Could not connect to database for restore.")
                return

            print("Successfully connected to database")
            cursor = connection.cursor()

            print("Disabling foreign key checks...")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

            executed = 0
            skipped = 0

            for i, statement in enumerate(statements):
                if statement.strip():
                    progress.setValue(executed)
                    progress.setLabelText(f"Restoring database: {executed}/{total_statements}")
                    if progress.wasCanceled():
                        print("Restore cancelled by user during execution")
                        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
                        cursor.close()
                        connection.close()
                        return
                    QApplication.processEvents()

                    try:
                        cursor.execute(statement)
                        connection.commit()
                        executed += 1
                    except Exception as stmt_error:
                        print(f"ERROR executing statement: {str(stmt_error)}")
                        skipped += 1

            print("Re-enabling foreign key checks...")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

            cursor.close()
            connection.close()
            print("Database connection closed")

            progress.setValue(total_statements)

            end_time = time.time()
            duration = end_time - start_time
            print(f"Restore completed in {duration:.2f} seconds")
            print(f"Statements: {executed} executed, {skipped} skipped")
            print("==== DATABASE RESTORE COMPLETED ====\n")

            success_msg = (
                f"Database restore completed successfully.\n\n"
                f"Statements: {executed} executed, {skipped} skipped\n"
                f"Time: {duration:.2f} seconds\n\n"
                "The application will now restart to apply the changes."
            )

            restart_msg = QMessageBox(self)
            restart_msg.setIcon(QMessageBox.Icon.Information)
            restart_msg.setWindowTitle("Restore Complete")
            restart_msg.setText(success_msg)
            restart_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            restart_msg.buttonClicked.connect(self.restart_application)
            restart_msg.exec()

        except Exception as e:
            print(f"CRITICAL ERROR during restore: {str(e)}")
            if 'progress' in locals(): progress.close()
            if 'cursor' in locals() and cursor: cursor.close()
            if 'connection' in locals() and connection and connection.is_connected(): connection.close()
            print("==== DATABASE RESTORE FAILED ====\n")
            QMessageBox.critical(self, "Restore Failed", f"Failed to restore database: {str(e)}")

    def restart_application(self):
        print("Application requires manual restart after database restore.")
        restart_message = QMessageBox(self)
        restart_message.setIcon(QMessageBox.Icon.Information)
        restart_message.setWindowTitle("Manual Restart Required")
        restart_message.setText(
            "Database has been restored successfully!\n\n"
            "Please close the application completely and restart it manually "
            "for the changes to take effect.\n\n"
            "Click OK to close the application."
        )
        restart_message.setStandardButtons(QMessageBox.StandardButton.Ok)
        result = restart_message.exec()
        if result == QMessageBox.StandardButton.Ok:
            print("User acknowledged. Closing application...")
            self.logout_requested.emit()
            QApplication.quit()
            print("Application closed.")

    def show_dashboard(self):
        self.content_area.setCurrentWidget(self.dashboard_page)
        self.refresh_dashboard_stats() # Ensure dashboard stats are fresh

    def manage_users(self):
        self.content_area.setCurrentWidget(self.users_page)
        self.load_users(self.role_filter.currentText()) # Refresh users when shown

    def manage_buildings(self): # New slot
        self.content_area.setCurrentWidget(self.buildings_page)
        self.load_buildings()

    def manage_facilities(self): # New slot
        self.content_area.setCurrentWidget(self.facilities_page)
        self.load_facilities()

    def manage_bookings(self): # Renamed slot
        self.content_area.setCurrentWidget(self.bookings_page)
        self.load_bookings() # Refresh bookings when shown

    def view_reports(self):
        self.content_area.setCurrentWidget(self.reports_page)
        self.refresh_analytics() # Refresh reports when shown

    def system_settings(self):
        self.content_area.setCurrentWidget(self.settings_page)
        self.load_booking_rules() # Load rules when settings are shown

    def logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def auto_refresh(self):
        try:
            if QApplication.mouseButtons() != Qt.MouseButton.NoButton or self._skip_refresh:
                return

            current_widget = self.content_area.currentWidget()

            # Dashboard stats refresh
            if current_widget == self.dashboard_page:
                if not hasattr(self, '_dashboard_refresh_counter'): self._dashboard_refresh_counter = 0
                self._dashboard_refresh_counter += 1
                if self._dashboard_refresh_counter >= 6: # Every 3 seconds
                    self._dashboard_refresh_counter = 0
                    self.refresh_dashboard_stats()

            # Bookings page refresh
            elif current_widget == self.bookings_page:
                if not hasattr(self, '_bookings_refresh_counter'): self._bookings_refresh_counter = 0
                self._bookings_refresh_counter += 1
                if self._bookings_refresh_counter >= 3: # Every 1.5 seconds
                    self._bookings_refresh_counter = 0
                    if hasattr(self, 'booking_search_input') and not self.booking_search_input.text().strip():
                        self._skip_refresh = True
                        self.load_bookings(force_refresh=False)
                        self._skip_refresh = False

            # Users page refresh
            elif current_widget == self.users_page:
                if not hasattr(self, '_users_refresh_counter'): self._users_refresh_counter = 0
                self._users_refresh_counter += 1
                if self._users_refresh_counter >= 5: # Every 2.5 seconds
                    self._users_refresh_counter = 0
                    if hasattr(self, 'role_filter'):
                        self._skip_refresh = True
                        self.load_users(self.role_filter.currentText())
                        self._skip_refresh = False

            # Buildings page refresh
            elif current_widget == self.buildings_page:
                if not hasattr(self, '_buildings_refresh_counter'): self._buildings_refresh_counter = 0
                self._buildings_refresh_counter += 1
                if self._buildings_refresh_counter >= 10: # Every 5 seconds
                    self._buildings_refresh_counter = 0
                    self._skip_refresh = True
                    self.load_buildings()
                    self._skip_refresh = False
            
            # Facilities page refresh
            elif current_widget == self.facilities_page:
                if not hasattr(self, '_facilities_refresh_counter'): self._facilities_refresh_counter = 0
                self._facilities_refresh_counter += 1
                if self._facilities_refresh_counter >= 10: # Every 5 seconds
                    self._facilities_refresh_counter = 0
                    self._skip_refresh = True
                    self.load_facilities(self.facility_building_filter.currentData(), self.facility_type_filter.currentText())
                    self._skip_refresh = False

            # Reports page refresh
            elif current_widget == self.reports_page:
                if not hasattr(self, '_analytics_refresh_counter'): self._analytics_refresh_counter = 0
                self._analytics_refresh_counter += 1
                if self._analytics_refresh_counter >= 10: # Every 5 seconds
                    self._analytics_refresh_counter = 0
                    self._skip_refresh = True
                    self.refresh_analytics()
                    self._skip_refresh = False

        except Exception as e:
            print(f"Auto-refresh error in admin dashboard: {e}")

    def display_db_error_message(self, table, message="Database connection error. Please check your database connection."):
        table.setRowCount(1)
        table.setColumnCount(1)
        table.horizontalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        error_item = QTableWidgetItem(message)
        error_item.setForeground(Qt.GlobalColor.red)
        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        error_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        table.setItem(0, 0, error_item)

    def display_no_data_message(self, table, message):
        column_count = table.columnCount()
        headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else "" for i in range(column_count)]

        table.setRowCount(1)
        table.setColumnCount(1)

        info_item = QTableWidgetItem(message)
        info_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        info_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

        table.setItem(0, 0, info_item)
        table.horizontalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        table.setColumnCount(column_count)
        table.horizontalHeader().setVisible(True)
        for i in range(column_count):
            table.setHorizontalHeaderItem(i, QTableWidgetItem(headers[i]))
    
    def backfill_booking_numbers(self): # Renamed for clarity
        """Generate and set booking numbers for any bookings that don't have them"""
        try:
            bookings_without_numbers = execute_query("""
                SELECT booking_id, created_at
                FROM bookings
                WHERE booking_number IS NULL OR booking_number = ''
                ORDER BY booking_id
            """)
            
            if not bookings_without_numbers:
                QMessageBox.information(self, "Booking Numbers", "All bookings already have booking numbers assigned.")
                return
            
            count = 0
            for booking in bookings_without_numbers:
                booking_id = booking['booking_id']
                booking_date = booking.get('created_at', datetime.datetime.now())
                booking_number = f"BKG-{booking_date.strftime('%Y%m%d')}-{booking_id:04d}"
                
                update_booking_number_query = """
                UPDATE bookings SET booking_number = %s WHERE booking_id = %s
                """
                result = execute_query(update_booking_number_query, (booking_number, booking_id), fetch=False)
                if result is not None:
                    count += 1
            
            self.load_bookings()
            QMessageBox.information(
                self, 
                "Booking Numbers Generated", 
                f"Successfully generated booking numbers for {count} bookings."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate booking numbers: {str(e)}"
            )

    def refresh_dashboard_stats(self):
        try:
            # Update facility count
            facility_count = execute_query("SELECT COUNT(*) as count FROM facilities")
            if facility_count and hasattr(self, 'stat_widgets') and 'facility_count_value' in self.stat_widgets:
                self.stat_widgets['facility_count_value'].setText(str(facility_count[0]['count']))

            # Update user count
            user_count = execute_query("SELECT COUNT(*) as count FROM users WHERE role IN ('student', 'faculty')")
            if user_count and hasattr(self, 'stat_widgets') and 'user_count_value' in self.stat_widgets:
                self.stat_widgets['user_count_value'].setText(str(user_count[0]['count']))

            # Update today's bookings
            today_bookings = execute_query("SELECT COUNT(*) as count FROM bookings WHERE DATE(start_time) = CURDATE() AND status != 'Cancelled'")
            if today_bookings and hasattr(self, 'stat_widgets') and 'today_bookings_value' in self.stat_widgets:
                self.stat_widgets['today_bookings_value'].setText(str(today_bookings[0]['count']))

            # Update total booking hours
            total_booking_hours = execute_query("SELECT SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60 as total FROM bookings WHERE status = 'Confirmed'")
            if total_booking_hours and total_booking_hours[0]['total'] is not None and hasattr(self, 'stat_widgets') and 'total_booking_hours_value' in self.stat_widgets:
                self.stat_widgets['total_booking_hours_value'].setText(f"{float(total_booking_hours[0]['total']):.1f} hrs")
            elif hasattr(self, 'stat_widgets') and 'total_booking_hours_value' in self.stat_widgets:
                self.stat_widgets['total_booking_hours_value'].setText("0.0 hrs")

            # Update recent bookings table
            if hasattr(self, 'recent_bookings_table'):
                recent_bookings = execute_query("""
                    SELECT bk.booking_id, bk.booking_number, u.username as user_name, f.name as facility_name,
                           bk.start_time, bk.end_time, bk.status
                    FROM bookings bk
                    JOIN users u ON bk.user_id = u.user_id
                    JOIN facilities f ON bk.facility_id = f.facility_id
                    ORDER BY bk.created_at DESC
                    LIMIT 5
                """)

                if recent_bookings:
                    current_row_count = self.recent_bookings_table.rowCount()
                    new_row_count = len(recent_bookings)
                    if current_row_count != new_row_count:
                        self.recent_bookings_table.setRowCount(new_row_count)

                    for i, booking in enumerate(recent_bookings):
                        self.recent_bookings_table.setItem(i, 0, QTableWidgetItem(booking['booking_number']))
                        self.recent_bookings_table.setItem(i, 1, QTableWidgetItem(booking['user_name']))
                        self.recent_bookings_table.setItem(i, 2, QTableWidgetItem(booking['facility_name']))

                        time_str = f"{booking['start_time'].strftime('%m-%d %H:%M')} to {booking['end_time'].strftime('%H:%M')}"
                        self.recent_bookings_table.setItem(i, 3, QTableWidgetItem(time_str))

                        status_item = QTableWidgetItem(booking['status'])
                        if booking['status'] == 'Confirmed': status_item.setForeground(Qt.GlobalColor.darkGreen)
                        elif booking['status'] == 'Cancelled': status_item.setForeground(Qt.GlobalColor.red)
                        elif booking['status'] == 'Pending Approval': status_item.setForeground(Qt.GlobalColor.darkYellow)
                        self.recent_bookings_table.setItem(i, 4, status_item)
                else:
                    self.recent_bookings_table.setRowCount(0) # Clear if no bookings
        except Exception as e:
            # Silent exception handling for dashboard refresh
            pass


# --- New Dialogs for SCNFBS ---
class BuildingDialog(QDialog):
    def __init__(self, parent=None, building=None):
        super().__init__(parent)
        self.building = building
        self.setWindowTitle("Edit Building" if building else "Add New Building")
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; color: white; }
            QLabel { color: white; font-size: 12px; }
            QLineEdit { background-color: #34495e; color: white; border: 1px solid #7f8c8d; border-radius: 4px; padding: 5px; min-height: 25px; }
            QLineEdit:focus { border: 1px solid #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.initUI()

    def initUI(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit(self.building['name'] if self.building else '')
        self.address_input = QLineEdit(self.building['address'] if self.building else '')
        self.description_input = QTextEdit(self.building['description'] if self.building else '')
        self.description_input.setFixedHeight(80) # Make it multi-line
        self.latitude_input = QLineEdit(str(self.building['latitude']) if self.building and self.building['latitude'] else '')
        self.longitude_input = QLineEdit(str(self.building['longitude']) if self.building and self.building['longitude'] else '')

        layout.addRow("Building Name:", self.name_input)
        layout.addRow("Address:", self.address_input)
        layout.addRow("Description:", self.description_input)
        layout.addRow("Latitude:", self.latitude_input)
        layout.addRow("Longitude:", self.longitude_input)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_building)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)

    def save_building(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip()
        description = self.description_input.toPlainText().strip()
        latitude = float(self.latitude_input.text()) if self.latitude_input.text() else None
        longitude = float(self.longitude_input.text()) if self.longitude_input.text() else None

        if not name or not address:
            QMessageBox.warning(self, "Validation Error", "Building Name and Address are required.")
            return

        try:
            if self.building:
                # Update existing
                from db_utils import update_building
                result = update_building(self.building['building_id'], name, address, description, latitude, longitude)
            else:
                # Add new
                from db_utils import add_building
                result = add_building(name, address, description, latitude, longitude)

            if result is not None:
                QMessageBox.information(self, "Success", "Building saved successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save building.")
        except ValueError:
            QMessageBox.critical(self, "Input Error", "Latitude and Longitude must be valid numbers.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

class FacilityDialog(QDialog):
    def __init__(self, parent=None, facility=None):
        super().__init__(parent)
        self.facility = facility
        self.setWindowTitle("Edit Facility" if facility else "Add New Facility")
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; color: white; }
            QLabel { color: white; font-size: 12px; }
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QCheckBox { background-color: #34495e; color: white; border: 1px solid #7f8c8d; border-radius: 4px; padding: 5px; min-height: 25px; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus { border: 1px solid #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
            QCheckBox { color: white; }
        """)
        self.initUI()

    def initUI(self):
        layout = QFormLayout(self)

        self.building_combo = QComboBox()
        self.load_buildings_into_combo(self.building_combo)
        if self.facility:
            index = self.building_combo.findData(self.facility['building_id'])
            if index >= 0:
                self.building_combo.setCurrentIndex(index)
        layout.addRow("Building:", self.building_combo)

        self.name_input = QLineEdit(self.facility['name'] if self.facility else '')
        layout.addRow("Facility Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Study Room", "Lecture Hall", "Lab", "Sports Venue", "Meeting Room", "Other"])
        if self.facility:
            index = self.type_combo.findText(self.facility['type'])
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        layout.addRow("Type:", self.type_combo)

        self.capacity_input = QSpinBox()
        self.capacity_input.setMinimum(1)
        self.capacity_input.setMaximum(1000)
        if self.facility:
            self.capacity_input.setValue(self.facility['capacity'])
        layout.addRow("Capacity:", self.capacity_input)
        
        self.description_input = QTextEdit(self.facility['description'] if self.facility else '')
        self.description_input.setFixedHeight(60)
        layout.addRow("Description:", self.description_input)

        self.is_bookable_checkbox = QCheckBox("Is Bookable?")
        self.is_bookable_checkbox.setChecked(self.facility['is_bookable'] if self.facility else True)
        layout.addRow("Booking Status:", self.is_bookable_checkbox)
        
        self.eligibility_combo = QComboBox()
        self.eligibility_combo.addItems(["any", "student", "faculty", "admin"])
        if self.facility:
            index = self.eligibility_combo.findText(self.facility['booking_eligibility_role'])
            if index >= 0:
                self.eligibility_combo.setCurrentIndex(index)
        layout.addRow("Eligible Role:", self.eligibility_combo)

        self.image_url_input = QLineEdit(self.facility['image_url'] if self.facility else '')
        layout.addRow("Image URL:", self.image_url_input)

        self.location_desc_input = QLineEdit(self.facility['location_description'] if self.facility else '')
        layout.addRow("Location Desc.:", self.location_desc_input)


        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_facility)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)

    def load_buildings_into_combo(self, combo_box):
        try:
            buildings = execute_query("SELECT building_id, name FROM buildings ORDER BY name")
            if not buildings:
                QMessageBox.warning(self, "No Buildings", "Please add buildings first before adding facilities.")
                return
            for building in buildings:
                combo_box.addItem(building['name'], building['building_id'])
        except Exception as e:
            print(f"Error loading buildings for facility dialog: {e}")
            QMessageBox.critical(self, "DB Error", "Failed to load buildings for facility. See console.")

    def save_facility(self):
        building_id = self.building_combo.currentData()
        name = self.name_input.text().strip()
        facility_type = self.type_combo.currentText()
        capacity = self.capacity_input.value()
        description = self.description_input.toPlainText().strip()
        is_bookable = self.is_bookable_checkbox.isChecked()
        eligibility_role = self.eligibility_combo.currentText()
        image_url = self.image_url_input.text().strip()
        location_desc = self.location_desc_input.text().strip()

        if not building_id or not name:
            QMessageBox.warning(self, "Validation Error", "Building and Facility Name are required.")
            return

        try:
            if self.facility:
                from db_utils import update_facility
                result = update_facility(
                    self.facility['facility_id'], building_id, name, facility_type, capacity, description,
                    is_bookable, eligibility_role, image_url, location_desc
                )
            else:
                from db_utils import add_facility
                result = add_facility(
                    building_id, name, facility_type, capacity, description,
                    is_bookable, eligibility_role, image_url, location_desc
                )

            if result is not None:
                QMessageBox.information(self, "Success", "Facility saved successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save facility.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

class BookingRuleDialog(QDialog):
    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("Edit Booking Rule" if rule else "Add New Booking Rule")
        self.setStyleSheet("""
            QDialog { background-color: #2c3e50; color: white; }
            QLabel { color: white; font-size: 12px; }
            QLineEdit, QComboBox, QSpinBox, QCheckBox { background-color: #34495e; color: white; border: 1px solid #7f8c8d; border-radius: 4px; padding: 5px; min-height: 25px; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
            QCheckBox { color: white; }
        """)
        self.initUI()

    def initUI(self):
        layout = QFormLayout(self)

        self.facility_type_combo = QComboBox()
        self.facility_type_combo.addItems(["Study Room", "Lecture Hall", "Lab", "Sports Venue", "Meeting Room", "Other"])
        if self.rule:
            self.facility_type_combo.setCurrentText(self.rule['facility_type'])
            self.facility_type_combo.setEnabled(False) # Prevent changing type for existing rule
        layout.addRow("Facility Type:", self.facility_type_combo)

        self.max_duration_input = QSpinBox()
        self.max_duration_input.setMinimum(15)
        self.max_duration_input.setMaximum(1440) # 24 hours in minutes
        self.max_duration_input.setSuffix(" minutes")
        if self.rule:
            self.max_duration_input.setValue(self.rule['max_booking_duration_minutes'])
        layout.addRow("Max Duration:", self.max_duration_input)

        self.min_advance_input = QSpinBox()
        self.min_advance_input.setMinimum(0)
        self.min_advance_input.setMaximum(720) # 30 days in hours
        self.min_advance_input.setSuffix(" hours")
        if self.rule:
            self.min_advance_input.setValue(self.rule['min_booking_advance_hours'])
        layout.addRow("Min Advance Notice:", self.min_advance_input)

        self.max_concurrent_input = QSpinBox()
        self.max_concurrent_input.setMinimum(0) # 0 for no limit
        self.max_concurrent_input.setMaximum(10)
        if self.rule:
            self.max_concurrent_input.setValue(self.rule['max_concurrent_bookings_per_user'])
        layout.addRow("Max Concurrent Bookings per User:", self.max_concurrent_input)

        self.can_recur_checkbox = QCheckBox("Can Be Recurring?")
        self.can_recur_checkbox.setChecked(self.rule['can_recur'] if self.rule else False)
        layout.addRow("Recurring:", self.can_recur_checkbox)

        self.applies_to_roles_input = QLineEdit(self.rule['applies_to_roles'] if self.rule else 'student,faculty,admin,any')
        self.applies_to_roles_input.setPlaceholderText("Comma-separated roles (e.g., student,faculty)")
        layout.addRow("Applies to Roles:", self.applies_to_roles_input)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_rule)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)

    def save_rule(self):
        facility_type = self.facility_type_combo.currentText()
        max_duration = self.max_duration_input.value()
        min_advance = self.min_advance_input.value()
        max_concurrent = self.max_concurrent_input.value()
        can_recur = self.can_recur_checkbox.isChecked()
        applies_to_roles = self.applies_to_roles_input.text().strip()

        if not facility_type or not applies_to_roles:
            QMessageBox.warning(self, "Validation Error", "Facility Type and Applicable Roles are required.")
            return
        
        # Basic validation for roles string
        valid_roles = ['student', 'faculty', 'admin', 'any']
        input_roles = [role.strip() for role in applies_to_roles.split(',')]
        if not all(role in valid_roles for role in input_roles):
            QMessageBox.warning(self, "Validation Error", f"Invalid roles in 'Applies to Roles'. Valid roles: {', '.join(valid_roles)}")
            return


        try:
            if self.rule:
                # Update existing rule
                from db_utils import update_booking_rule
                result = update_booking_rule(
                    self.rule['rule_id'], max_duration, min_advance, max_concurrent, can_recur, applies_to_roles
                )
            else:
                # Add new rule
                from db_utils import add_booking_rule
                result = add_booking_rule(
                    facility_type, max_duration, min_advance, max_concurrent, can_recur, applies_to_roles
                )

            if result is not None:
                QMessageBox.information(self, "Success", "Booking rule saved successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save booking rule.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")