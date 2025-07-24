from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox, QSpinBox, QTextEdit,QGroupBox, QApplication,
    QDoubleSpinBox, QTabWidget, QDateEdit, QProgressBar, QMenu, QDateTimeEdit
)
from PySide6.QtCore import QRunnable, QThreadPool, Signal, QObject
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime, QThread
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor
from db_utils import execute_query, get_facility_availability, create_booking, cancel_booking, get_user_bookings # Import relevant SCNFBS DB functions
import matplotlib.pyplot as plt
import numpy as np
import re 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # Use QTAgg for better integration
from matplotlib.figure import Figure
import datetime # Import the datetime module explicitly
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AvailabilityWorker(QObject):
    finished = Signal(list)

    def __init__(self, facility_id, date_str):
        super().__init__()
        self.facility_id = facility_id
        self.date_str = date_str

    def run(self):
        try:
            booked_slots = get_facility_availability(self.facility_id, self.date_str)
            self.finished.emit(booked_slots)
        except Exception as e:
            print(f"Worker error: {e}")
            self.finished.emit([])

class FacultyDashboard(QWidget):
    logout_requested = Signal()

    def __init__(self, user):
        self.reminder_popup_shown = False
        super().__init__()
        self.user = user
        self.user_id = user.user_id # Access user ID directly from the User object
        
        # Initialize booking layouts dictionary
        self.booking_layouts = {
            'Upcoming': None,
            'Past': None,
            'Cancelled': None
        }

        self.initUI()

        # Load initial data
        self.load_dashboard_stats()
        self.load_facilities_for_booking() # Load facilities when dashboard starts

        # Set up auto-refresh timer for bookings and dashboard
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(500)  # 0.5 seconds for real-time updates
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start()

    def initUI(self):
        self.setWindowTitle("Smart Campus - Faculty/Staff Dashboard") # Updated Title

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

        welcome_label = QLabel(f"Welcome, {self.user.username}")
        welcome_label.setObjectName("welcome-label")
        welcome_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        # User's role label
        user_role_label = QLabel(self.user.role.name.capitalize())
        user_role_label.setObjectName("user-role")

        user_info_layout.addWidget(welcome_label)
        user_info_layout.addWidget(user_role_label)
        sidebar_layout.addWidget(user_info)

        # Navigation buttons - Updated for SCNFBS
        nav_buttons = [
            {"text": "Dashboard", "icon": "📊", "slot": self.show_dashboard},
            {"text": "My Bookings", "icon": "📅", "slot": self.manage_my_bookings}, # Renamed from Orders
            {"text": "Book Facilities", "icon": "📍", "slot": self.book_facilities}, # Renamed from Menu
            {"text": "My Profile", "icon": "👤", "slot": self.show_profile_page}, # Renamed from Restaurant Profile
            {"text": "View Usage", "icon": "📈", "slot": self.view_my_usage_reports} # Renamed from Reports
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

        # Content area with stacked pages
        self.content_area = QStackedWidget()

        # Create pages
        self.dashboard_page = self.create_dashboard_page()
        self.my_bookings_page = self.create_my_bookings_page() # New
        self.book_facilities_page = self.create_book_facilities_page() # New
        self.profile_page = self.create_profile_page()
        self.my_usage_reports_page = self.create_my_usage_reports_page() # New

        # Add pages to stacked widget
        self.content_area.addWidget(self.dashboard_page)
        self.content_area.addWidget(self.my_bookings_page)
        self.content_area.addWidget(self.book_facilities_page)
        self.content_area.addWidget(self.profile_page)
        self.content_area.addWidget(self.my_usage_reports_page)

        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_area)

        # Apply styles (kept largely similar, adjust as needed)
        self.setStyleSheet("""
                        
    QLabel {
    color: black;
}
       QComboBox {
        background-color: white ;
        color: black;
    }

    QComboBox QAbstractItemView {
        background-color: white ;
        color: black;
        selection-background-color: #dcd2c4;
        selection-color: black;
    }                    

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
            #user-role {
                color: #3498db;
                font-size: 14px;
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
            QFrame#stat-card {
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
            #booking-card {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
                border: 1px solid #ddd;
            }
            #booking-id {
                color: #2c3e50;
            }
            #booking-time {
                color: #7f8c8d;
                font-size: 12px;
            }
            #facility-info {
                color: #34495e;
            }
            #booking-status {
                font-weight: bold;
            }
        """)

        # Start with dashboard
        self.show_dashboard()

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header
        header = QLabel("Faculty/Staff Dashboard")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 24))

        # Stats overview - Updated for SCNFBS
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)

        # Create stat cards with empty data (will be populated in load_dashboard_stats)
        self.stat_cards = {
            "upcoming_bookings": {"title": "Upcoming Bookings", "value": "0", "icon": "➡️", "widget": None},
            "past_bookings": {"title": "Past Bookings", "value": "0", "icon": "⬅️", "widget": None},
            "total_booking_hours": {"title": "Total Booked Hrs", "value": "0.0 hrs", "icon": "⏰", "widget": None},
            "facilities_available": {"title": "Facilities Available", "value": "0", "icon": "✅", "widget": None},
            "booking_reminders": {"title": "Reminders", "value": "0", "icon": "🔔", "widget": None}  # ✅ New reminder card
        }

        for key, card in self.stat_cards.items():
            card_widget = QFrame()
            card_widget.setObjectName("stat-card")
            card_layout = QVBoxLayout(card_widget)

            title = QLabel(f"{card['icon']} {card['title']}")
            title.setObjectName("stat-title")

            value = QLabel(card["value"])
            value.setObjectName("stat-value")
            value.setFont(QFont("Arial", 20, QFont.Weight.Bold))

            card_layout.addWidget(title)
            card_layout.addWidget(value)

            stats_layout.addWidget(card_widget)

            # Store value label reference for later updates
            card["widget"] = value

        # Recent bookings section - Updated from Recent Orders
        recent_bookings_label = QLabel("Recent Bookings")
        recent_bookings_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        # Add refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(recent_bookings_label)
        refresh_layout.addStretch()

        refresh_btn = QPushButton("Refresh Dashboard")
        refresh_btn.setObjectName("action-button")
        refresh_btn.clicked.connect(self.load_dashboard_stats)
        refresh_layout.addWidget(refresh_btn)

        self.recent_bookings_table = QTableWidget()
        self.recent_bookings_table.setColumnCount(5)
        self.recent_bookings_table.setHorizontalHeaderLabels(["Booking #", "Facility", "Building", "Time", "Status"])
        self.recent_bookings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_bookings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_bookings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_bookings_table.setAlternatingRowColors(True)
        self.recent_bookings_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")
        # Add to layout
        layout.addWidget(header)
        layout.addWidget(stats_frame)
        layout.addSpacing(20)
        layout.addLayout(refresh_layout)
        layout.addWidget(self.recent_bookings_table)

        return page

    def create_my_bookings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header
        header = QLabel("My Bookings")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setFont(QFont("Arial", 24))

        # Search and filter bar
        search_layout = QHBoxLayout()

        # Search input for facility name
        search_label = QLabel("Search:")
        self.bookings_search_input = QLineEdit()
        self.bookings_search_input.setPlaceholderText("Search by facility or building name...")
        self.bookings_search_input.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        # Date range for bookings
        date_label = QLabel("Date:")

        self.bookings_start_date = QDateEdit()
        self.bookings_start_date.setCalendarPopup(True)
        self.bookings_start_date.setDisplayFormat("yyyy-MM-dd")  # Ensure visible and editable
        self.bookings_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.bookings_start_date.setMinimumDate(QDate(2000, 1, 1))  # Optional: Prevent empty/invalid date
        self.bookings_start_date.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: black;
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

        to_label = QLabel("to")

        self.bookings_end_date = QDateEdit()
        self.bookings_end_date.setCalendarPopup(True)
        self.bookings_end_date.setDisplayFormat("yyyy-MM-dd")  # Same format
        self.bookings_end_date.setDate(QDate.currentDate().addMonths(3))
        self.bookings_end_date.setMinimumDate(QDate(2000, 1, 1))
        self.bookings_end_date.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: black;
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


        # Search button
        search_btn = QPushButton("Search")
        search_btn.setObjectName("action-button")
        search_btn.clicked.connect(self.search_my_bookings)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("action-button")
        refresh_btn.clicked.connect(self.load_all_my_bookings)

        # Add to layout
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.bookings_search_input, 3)
        search_layout.addWidget(date_label)
        search_layout.addWidget(self.bookings_start_date)
        search_layout.addWidget(to_label)
        search_layout.addWidget(self.bookings_end_date)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(refresh_btn)

        # Tab widget for different booking statuses
        tabs = QTabWidget()

        # Create tabs for different booking states
        upcoming_bookings_tab = self.create_bookings_tab("Upcoming")
        past_bookings_tab = self.create_bookings_tab("Past")
        cancelled_bookings_tab = self.create_bookings_tab("Cancelled")

        # Add tabs to widget
        tabs.addTab(upcoming_bookings_tab, "Upcoming Bookings")
        tabs.addTab(past_bookings_tab, "Past Bookings")
        tabs.addTab(cancelled_bookings_tab, "Cancelled Bookings")

        layout.addWidget(header)
        layout.addLayout(search_layout)
        layout.addWidget(tabs)

        # Store tab references
        self.booking_tabs = {
            "Upcoming": upcoming_bookings_tab,
            "Past": past_bookings_tab,
            "Cancelled": cancelled_bookings_tab
        }

        # Load orders
        self.load_all_my_bookings()

        return page

    def create_bookings_tab(self, status):
        """Create a tab for bookings with the given status"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create scroll area for bookings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Content widget
        content = QWidget()
        self.booking_layouts[status] = QVBoxLayout(content)
        self.booking_layouts[status].setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return tab

    def load_all_my_bookings(self):
        """Load bookings for all tabs for the logged-in user"""
        # Clear existing bookings
        for status, layout in self.booking_layouts.items():
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Add "No bookings" message to each tab initially
        for status, layout in self.booking_layouts.items():
            no_bookings = QLabel(f"No {status.lower()} bookings")
            no_bookings.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_bookings)

        # Get all bookings for this user
        try:
            # get_user_bookings is a new function in db_utils
            my_bookings = get_user_bookings(self.user_id)

            if not my_bookings:
                return

            # Clear "No bookings" messages
            for status, layout in self.booking_layouts.items():
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            # Group by status (Upcoming, Past, Cancelled)
            now = datetime.datetime.now()
            
            for booking in my_bookings:
                tab_status = "Upcoming" # Default
                if booking['status'] == 'Cancelled':
                    tab_status = "Cancelled"
                elif booking['end_time'] < now and booking['status'] == 'Confirmed':
                    tab_status = "Past"
                    execute_query("UPDATE bookings SET status = 'Completed' WHERE booking_id = %s", (booking['booking_id'],), fetch=False)
                    booking['status'] = 'Completed' # Update locally for display
                elif booking['end_time'] < now:
                    tab_status = "Past"
                
                self.add_booking_card(booking, tab_status)

        except Exception as e:
            print(f"Error loading my bookings: {e}")
            self.show_error_message("Error", f"Failed to load your bookings: {str(e)}")

    def add_booking_card(self, booking, tab_status):
        """Add a booking card to the appropriate tab"""
        card = QFrame()
        card.setObjectName("booking-card")
        card_layout = QVBoxLayout(card)

        # Booking header
        header_layout = QHBoxLayout()

        booking_number_label = QLabel(f"Booking {booking['booking_number']}")
        booking_number_label.setObjectName("booking-id")
        booking_number_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        time_label = QLabel(f"{booking['start_time'].strftime('%Y-%m-%d %H:%M')} - {booking['end_time'].strftime('%H:%M')}")
        time_label.setObjectName("booking-time")

        header_layout.addWidget(booking_number_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)

        # Status label
        status_layout = QHBoxLayout()
        status_label = QLabel("Status:")
        status_value = QLabel(booking['status'])

        # Set color based on status
        status_color = "#95a5a6"  # Default gray
        if booking['status'] == "Confirmed":
            status_color = "#2ecc71"  # Green
        elif booking['status'] == "Pending Approval":
            status_color = "#f39c12"  # Orange
        elif booking['status'] == "Completed":
            status_color = "#3498db"  # Blue
        elif booking['status'] == "Cancelled":
            status_color = "#e74c3c"  # Red

        status_value.setStyleSheet(f"color: {status_color}; font-weight: bold;")

        status_layout.addWidget(status_label)
        status_layout.addWidget(status_value)
        status_layout.addStretch()

        # Facility info
        facility_label = QLabel(f"Facility: {booking['facility_name']} ({booking['building_name']})")
        facility_label.setObjectName("facility-info")
        
        purpose_label = QLabel(f"Purpose: {booking['purpose']}")
        
        # Action buttons based on tab status
        buttons_layout = QHBoxLayout()

        if tab_status == "Upcoming":
            cancel_btn = QPushButton("Cancel Booking")
            cancel_btn.setObjectName("delete-button")
            cancel_btn.clicked.connect(lambda: self.cancel_my_booking(booking['booking_id']))
            buttons_layout.addWidget(cancel_btn)
        
        # Add all components to card
        card_layout.addLayout(header_layout)
        card_layout.addLayout(status_layout)
        card_layout.addWidget(facility_label)
        card_layout.addWidget(purpose_label)
        card_layout.addLayout(buttons_layout)

        # Add card to appropriate layout
        if tab_status in self.booking_layouts:
            self.booking_layouts[tab_status].addWidget(card)

    def cancel_my_booking(self, booking_id):
        """Cancel a user's booking"""
        reply = self.show_question_message(
            "Confirm Cancellation",
            "Are you sure you want to cancel this booking? This action cannot be undone."
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = cancel_booking(booking_id) # Uses the function from db_utils

            if result:
                self.show_info_message(
    "📧 Email",
    "Dear Faculty,\n\nYour booking has been cancelled.\n\nRegards,\nSmart Campus Team"
)

                self.load_all_my_bookings() # Refresh the bookings list
                self.load_dashboard_stats() # Update dashboard stats
            else:
                self.show_error_message("Error", "Failed to cancel booking.")

    def search_my_bookings(self):
        search_term = self.bookings_search_input.text().strip()
        start_date = self.bookings_start_date.date().toString("yyyy-MM-dd")
        end_date = self.bookings_end_date.date().toString("yyyy-MM-dd")

        # Clear existing bookings in all tabs
        for status, layout in self.booking_layouts.items():
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # Add "No bookings" message to each tab initially
        for status, layout in self.booking_layouts.items():
            no_bookings = QLabel(f"No {status.lower()} bookings found matching criteria.")
            no_bookings.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_bookings)

        try:
            # Adapt get_user_bookings to handle search term as well
            # This requires a modification to get_user_bookings in db_utils to accept search_term
            # For now, let's construct the query directly or assume get_user_bookings is extended
            
            query = """
                SELECT bk.*, f.name as facility_name, bu.name as building_name
                FROM bookings bk
                JOIN facilities f ON bk.facility_id = f.facility_id
                JOIN buildings bu ON f.building_id = bu.building_id
                WHERE bk.user_id = %s
            """
            params = [self.user_id]

            if search_term:
                query += " AND (f.name LIKE %s OR bu.name LIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])

            if start_date:
                query += " AND DATE(bk.start_time) >= %s"
                params.append(start_date)

            if end_date:
                query += " AND DATE(bk.end_time) <= %s"
                params.append(end_date)

            query += " ORDER BY bk.start_time DESC"
            
            filtered_bookings = execute_query(query, params)

            if not filtered_bookings:
                return # Keep "No bookings found" messages

            # Clear "No bookings" messages again as we have data
            for status, layout in self.booking_layouts.items():
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            now = datetime.datetime.now()
            for booking in filtered_bookings:
                tab_status = "Upcoming"
                if booking['status'] == 'Cancelled':
                    tab_status = "Cancelled"
                elif booking['end_time'] < now and booking['status'] == 'Confirmed':
                    tab_status = "Past"
                    execute_query("UPDATE bookings SET status = 'Completed' WHERE booking_id = %s", (booking['booking_id'],), fetch=False)
                    booking['status'] = 'Completed' # Update locally for display
                elif booking['end_time'] < now:
                    tab_status = "Past"
                
                self.add_booking_card(booking, tab_status)

        except Exception as e:
            print(f"Error searching my bookings: {e}")
            self.show_error_message("Error", f"Failed to search bookings: {str(e)}")

    #Book facility page
    def create_book_facilities_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Book Facilities")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()
          # Add a date selector for booking
        date_selection_layout = QHBoxLayout()
        date_selection_layout.addWidget(QLabel("Select Booking Date:"))
        self.booking_date_selector = QDateEdit(calendarPopup=True)
        self.booking_date_selector.setDate(QDate.currentDate())
        self.booking_date_selector.setStyleSheet("QDateEdit { background-color: white; color: black; }") # Style for QDateEdit
        date_selection_layout.addWidget(self.booking_date_selector)
        date_selection_layout.addStretch()
        header_layout.addLayout(date_selection_layout) # Add this to your header layout or main layout
        
        # Search and filter for facilities
        filter_group = QGroupBox("Filter Facilities")
        filter_group.setObjectName("filter-box")  # ✅ Add this line

        filter_layout = QFormLayout(filter_group)

        self.facility_search_input = QLineEdit()
        self.facility_search_input.setPlaceholderText("Search by name or description")
        filter_layout.addRow("Keyword:", self.facility_search_input)
        self.facility_search_input.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        self.facility_building_filter = QComboBox()
        self.facility_building_filter.addItem("All Buildings", None)
        self.load_buildings_into_combo(self.facility_building_filter)
        filter_layout.addRow("Building:", self.facility_building_filter)
        self.facility_building_filter.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        self.facility_type_filter = QComboBox()
        self.facility_type_filter.addItems(["All Types", "Study Room", "Lecture Hall", "Lab", "Sports Venue", "Meeting Room", "Other"])
        filter_layout.addRow("Type:", self.facility_type_filter)
        self.facility_type_filter.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        self.facility_capacity_spinbox = QSpinBox()
        self.facility_capacity_spinbox.setMinimum(0) # 0 for any capacity
        self.facility_capacity_spinbox.setMaximum(500)
        filter_layout.addRow("Min Capacity:", self.facility_capacity_spinbox)
        self.facility_capacity_spinbox.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")

        filter_buttons_layout = QHBoxLayout()
        search_facilities_btn = QPushButton("Search Available Facilities")
        search_facilities_btn.setObjectName("action-button")
        search_facilities_btn.clicked.connect(self.load_facilities_for_booking)
        filter_buttons_layout.addStretch()
        filter_buttons_layout.addWidget(search_facilities_btn)
        filter_layout.addRow(filter_buttons_layout)


        # Facilities table
        self.available_facilities_table = QTableWidget()
        self.available_facilities_table.setColumnCount(6)
        self.available_facilities_table.setHorizontalHeaderLabels(["ID", "Facility Name", "Building", "Type", "Capacity", "Actions"])
        self.available_facilities_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.available_facilities_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.available_facilities_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.available_facilities_table.setAlternatingRowColors(True)
        self.available_facilities_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")
        layout.addLayout(header_layout)
        layout.addWidget(filter_group)
        layout.addWidget(self.available_facilities_table)

        return page

    def load_buildings_into_combo(self, combo_box):
        """Helper to load buildings into a QComboBox."""
        try:
            buildings = execute_query("SELECT building_id, name FROM buildings ORDER BY name")
            for building in buildings:
                combo_box.addItem(building['name'], building['building_id'])
        except Exception as e:
            print(f"Error loading buildings for combo box: {e}")

    def load_facilities_for_booking(self):
        """Load facilities suitable for booking based on filters."""
        self.available_facilities_table.setRowCount(0) # Clear previous results initially

        search_term = self.facility_search_input.text().strip()
        building_id = self.facility_building_filter.currentData()
        facility_type = self.facility_type_filter.currentText()
        min_capacity = self.facility_capacity_spinbox.value()

        if facility_type == "All Types":
            facility_type = None

        try:
            # Start building the query
            query = """
                SELECT f.*, b.name as building_name
                FROM facilities f
                JOIN buildings b ON f.building_id = b.building_id
                WHERE f.is_bookable = TRUE
                AND (f.booking_eligibility_role = %s OR f.booking_eligibility_role = 'any')
            """
            params = [self.user.role.value]

            # Add search term filter
            if search_term:
                query += " AND (f.name LIKE %s OR f.description LIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])

            # Add building filter
            if building_id:
                query += " AND f.building_id = %s"
                params.append(building_id)

            # Add facility type filter
            if facility_type and facility_type != "All Types": # Double-check for "All Types"
                query += " AND f.type = %s"
                params.append(facility_type)

            # Add minimum capacity filter
            if min_capacity > 0: # Only apply if greater than 0
                query += " AND f.capacity >= %s"
                params.append(min_capacity)

            query += " ORDER BY f.name" # Optional: Order results

            facilities_data = execute_query(query, tuple(params)) # Pass parameters as a tuple

            if not facilities_data:
                self.display_no_data_message(self.available_facilities_table, "No bookable facilities found matching criteria.")
                return

            self.available_facilities_table.setRowCount(len(facilities_data))
            for row_idx, facility in enumerate(facilities_data):
                self.available_facilities_table.setItem(row_idx, 0, QTableWidgetItem(str(facility['facility_id'])))
                self.available_facilities_table.setItem(row_idx, 1, QTableWidgetItem(facility['name']))
                self.available_facilities_table.setItem(row_idx, 2, QTableWidgetItem(facility['building_name']))
                self.available_facilities_table.setItem(row_idx, 3, QTableWidgetItem(facility['type']))
                self.available_facilities_table.setItem(row_idx, 4, QTableWidgetItem(str(facility['capacity'])))

                # Action button: Book
                buttons_widget = QWidget()
                buttons_layout = QHBoxLayout(buttons_widget)
                buttons_layout.setContentsMargins(0, 0, 0, 0)
                buttons_layout.setSpacing(5)

                book_btn = QPushButton("Book Now")
                book_btn.setObjectName("action-button")
                book_btn.clicked.connect(lambda checked, f=facility: self.open_booking_dialog(f))

                buttons_layout.addWidget(book_btn)
                self.available_facilities_table.setCellWidget(row_idx, 5, buttons_widget)

        except Exception as e:
            print(f"Error loading facilities for booking: {e}")
            self.display_db_error_message(self.available_facilities_table, "Failed to load facilities due to an unexpected error.")

    def open_booking_dialog(self, facility):
        dialog = BookingDialog(self, self.user_id, facility, self.booking_date_selector.date().toPython())
        if dialog.exec():
            self.load_all_my_bookings() # Refresh my bookings
            self.load_dashboard_stats() # Refresh dashboard stats
    

    #Profile Page:
    def create_profile_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header
        header = QLabel("My Profile")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        # Form layout
        form_layout = QFormLayout()

        # Profile fields
        self.profile_username = QLineEdit(self.user.username)
        self.profile_username.setReadOnly(True)
        self.profile_username.setStyleSheet("background-color: #f0f0f0; color: #555;")

        self.profile_email = QLineEdit(self.user.email)
        self.profile_email.setPlaceholderText("Enter your email")

        self.profile_role = QLineEdit(self.user.role.name.capitalize())
        self.profile_role.setReadOnly(True)
        self.profile_role.setStyleSheet("background-color: #f0f0f0; color: #555;")

        # Add fields
        form_layout.addRow("Username:", self.profile_username)
        form_layout.addRow("Email:", self.profile_email)
        form_layout.addRow("Role:", self.profile_role)

        # Update Button Section
        button_layout = QHBoxLayout()
        self.update_email_btn = QPushButton("Update Email")  # ✅ Button added
        self.update_email_btn.setObjectName("action-button")
        self.update_email_btn.clicked.connect(self.save_profile)  # Connect to save_profile

        button_layout.addStretch()
        button_layout.addWidget(self.update_email_btn)

        # Add to main layout
        layout.addWidget(header)
        layout.addSpacing(10)
        layout.addLayout(form_layout)
        layout.addStretch()
        layout.addLayout(button_layout)

        # Optional styling
        page.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QPushButton#action-button {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton#action-button:hover {
                background-color: #2980b9;
            }
        """)

        return page


    def save_profile(self):
        """Save user profile details (e.g., email)"""
        new_email = self.profile_email.text().strip()

        if not new_email:
            self.show_warning_message("Validation Error", "Email cannot be empty.")
            return
        
        # Basic email format check
        if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            self.show_warning_message("Validation Error", "Please enter a valid email address.")
            return

        try:
            # Assuming db_utils has a function to update user details
            # If not, you'd add: update_user_email(user_id, new_email) in db_utils
            
            # For simplicity, directly using execute_query
            query = "UPDATE users SET email = %s WHERE user_id = %s"
            result = execute_query(query, (new_email, self.user_id), fetch=False)

            if result is not None:
                self.user.email = new_email # Update the user object in memory
                self.show_info_message("Success", "Your profile has been updated successfully!")
            else:
                self.show_error_message("Error", "Failed to update profile.")
        except Exception as e:
            self.show_error_message("Error", f"An error occurred: {str(e)}")


    def create_my_usage_reports_page(self):
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

        header = QLabel("My Usage Reports")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #ecf0f1; background-color: #2c3e50; padding: 10px; border-radius: 4px;")

        date_range_layout = QHBoxLayout()
        date_range_label = QLabel("Date Range:")
        date_range_label.setStyleSheet("color: #2c3e50;")
        self.reports_start_date_my = QDateEdit() # Renamed to avoid conflict
        self.reports_start_date_my.setCalendarPopup(True)
        self.reports_start_date_my.setDate(QDate.currentDate().addDays(-90)) # Last 3 months by default
        self.reports_end_date_my = QDateEdit() # Renamed to avoid conflict
        self.reports_end_date_my.setCalendarPopup(True)
        self.reports_end_date_my.setDate(QDate.currentDate())

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
        self.reports_start_date_my.setStyleSheet(date_style)
        self.reports_end_date_my.setStyleSheet(date_style)

        refresh_btn = QPushButton("Refresh Report")
        refresh_btn.setObjectName("action-button")
        refresh_btn.clicked.connect(self.refresh_my_analytics)

        date_range_layout.addWidget(date_range_label)
        date_range_layout.addWidget(self.reports_start_date_my)
        date_range_layout.addWidget(QLabel("to"))
        date_range_layout.addWidget(self.reports_end_date_my)
        date_range_layout.addStretch()
        date_range_layout.addWidget(refresh_btn)

        # Key metrics cards for personal usage
        metrics_layout = QHBoxLayout()

        total_bookings_card = QFrame()
        total_bookings_card.setObjectName("metric-card")
        total_bookings_layout = QVBoxLayout(total_bookings_card)
        self.my_total_bookings_label = QLabel("0")
        self.my_total_bookings_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        total_bookings_layout.addWidget(QLabel("Total Bookings"))
        total_bookings_layout.addWidget(self.my_total_bookings_label)

        total_hours_card = QFrame()
        total_hours_card.setObjectName("metric-card")
        total_hours_layout = QVBoxLayout(total_hours_card)
        self.my_total_hours_label = QLabel("0.0 hrs")
        self.my_total_hours_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        total_hours_layout.addWidget(QLabel("Total Booked Hours"))
        total_hours_layout.addWidget(self.my_total_hours_label)

        avg_duration_card = QFrame()
        avg_duration_card.setObjectName("metric-card")
        avg_duration_layout = QVBoxLayout(avg_duration_card)
        self.my_avg_duration_label = QLabel("0 min")
        self.my_avg_duration_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        avg_duration_layout.addWidget(QLabel("Avg. Booking Duration"))
        avg_duration_layout.addWidget(self.my_avg_duration_label)

        metrics_layout.addWidget(total_bookings_card)
        metrics_layout.addWidget(total_hours_card)
        metrics_layout.addWidget(avg_duration_card)

        # Charts section for personal usage
        charts_layout = QHBoxLayout()

        # Bookings by Status Chart (Personal)
        status_chart_card = QFrame()
        status_chart_card.setObjectName("chart-card")
        status_chart_layout = QVBoxLayout(status_chart_card)
        status_chart_layout.addWidget(QLabel("My Bookings by Status"))
        
        self.my_status_chart = QFrame()
        self.my_status_chart.setMinimumHeight(300)
        chart_layout = QVBoxLayout(self.my_status_chart)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        status_chart_layout.addWidget(self.my_status_chart)

        # Booking Trend Chart (Personal)
        booking_trend_card = QFrame()
        booking_trend_card.setObjectName("chart-card")
        booking_trend_layout = QVBoxLayout(booking_trend_card)
        booking_trend_layout.addWidget(QLabel("My Daily Booking Trend"))

        self.my_booking_trend_chart = QFrame()
        self.my_booking_trend_chart.setMinimumHeight(300)
        chart_layout = QVBoxLayout(self.my_booking_trend_chart)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        booking_trend_layout.addWidget(self.my_booking_trend_chart)

        charts_layout.addWidget(status_chart_card)
        charts_layout.addWidget(booking_trend_card)

        # Detailed Reports Section for personal usage
        reports_tabs = QTabWidget()
        reports_tabs.setMinimumHeight(300)

        # My Most Used Facilities Tab
        facilities_tab = QWidget()
        facilities_layout = QVBoxLayout(facilities_tab)
        self.my_top_facilities_table = QTableWidget()
        self.my_top_facilities_table.setColumnCount(4)
        self.my_top_facilities_table.setHorizontalHeaderLabels(["Facility Name", "Building", "Type", "Total Hours Booked"])
        self.my_top_facilities_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        facilities_layout.addWidget(self.my_top_facilities_table)

        reports_tabs.addTab(facilities_tab, "My Top Facilities")

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
            QDateEdit#date-picker {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 25px;
            }
            QDateEdit#date-picker::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid #7f8c8d;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QDateEdit#date-picker::down-arrow {
                image: url(ui/icons/calendar.png);
                width: 16px;
                height: 16px;
            }
            QDateEdit#date-picker:hover {
                background-color: #3d5a74;
                border: 1px solid #3498db;
            }
            QDateEdit#date-picker:focus {
                border: 2px solid #3498db;
            }
        """)

        self.refresh_my_analytics() # Load initial data
        return page

    def refresh_my_analytics(self):
        """Refresh personal usage analytics data based on selected date range"""
        start_date = self.reports_start_date_my.date().toString("yyyy-MM-dd")
        end_date_obj = self.reports_end_date_my.date().addDays(1)
        end_date = end_date_obj.toString("yyyy-MM-dd")

        try:
            # Get key metrics for this user
            metrics_query = """
                SELECT
                    COUNT(*) as total_bookings,
                    SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60 as total_booked_hours,
                    AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)) as avg_booking_duration_minutes
                FROM bookings
                WHERE user_id = %s
                AND start_time BETWEEN %s AND %s AND status IN ('Confirmed', 'Completed')
            """
            metrics = execute_query(metrics_query, (self.user_id, start_date, end_date))

            if metrics and metrics[0]:
                self.my_total_bookings_label.setText(str(metrics[0]['total_bookings'] or 0))
                self.my_total_hours_label.setText(f"{float(metrics[0]['total_booked_hours'] or 0):.1f} hrs")
                self.my_avg_duration_label.setText(f"{int(metrics[0]['avg_booking_duration_minutes'] or 0)} min")
            else:
                self.my_total_bookings_label.setText("0")
                self.my_total_hours_label.setText("0.0 hrs")
                self.my_avg_duration_label.setText("0 min")


            # Get bookings by status (Personal)
            status_query = """
                SELECT status, COUNT(*) as count
                FROM bookings
                WHERE user_id = %s AND start_time BETWEEN %s AND %s
                GROUP BY status
            """
            status_data = execute_query(status_query, (self.user_id, start_date, end_date))

            # Get booking trend (Personal)
            booking_trend_query = """
                SELECT DATE(start_time) as date, COUNT(*) as count
                FROM bookings
                WHERE user_id = %s AND start_time BETWEEN %s AND %s AND status IN ('Confirmed', 'Completed')
                GROUP BY DATE(start_time)
                ORDER BY date
            """
            booking_trend_data = execute_query(booking_trend_query, (self.user_id, start_date, end_date))

            # Clear previous charts
            for i in reversed(range(self.my_status_chart.layout().count())):
                widget = self.my_status_chart.layout().itemAt(i).widget()
                if widget: widget.setParent(None)

            for i in reversed(range(self.my_booking_trend_chart.layout().count())):
                widget = self.my_booking_trend_chart.layout().itemAt(i).widget()
                if widget: widget.setParent(None)

            # Create status pie chart (Personal)
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
                self.my_status_chart.layout().addWidget(status_canvas)
                status_fig.tight_layout()
                status_canvas.draw()

            # Create booking trend chart (Personal)
            if booking_trend_data:
                booking_trend_fig = Figure(figsize=(5, 4), dpi=100)
                booking_trend_canvas = FigureCanvas(booking_trend_fig)
                ax = booking_trend_fig.add_subplot(111)

                dates = [item['date'] for item in booking_trend_data]
                counts = [item['count'] for item in booking_trend_data]

                ax.plot(dates, counts, 'o-', color='#3498db', linewidth=2)
                ax.set_title('My Daily Confirmed Bookings')
                ax.set_ylabel('Number of Bookings')
                ax.grid(True, linestyle='--', alpha=0.7)

                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

                self.my_booking_trend_chart.layout().addWidget(booking_trend_canvas)
                booking_trend_fig.tight_layout()
                booking_trend_canvas.draw()

            # Get my top facilities (by total hours booked)
            facilities_query = """
                SELECT
                    f.name,
                    b.name as building_name,
                    f.type,
                    SUM(TIMESTAMPDIFF(MINUTE, bk.start_time, bk.end_time)) / 60 as total_hours
                FROM facilities f
                JOIN buildings b ON f.building_id = b.building_id
                JOIN bookings bk ON f.facility_id = bk.facility_id
                WHERE bk.user_id = %s AND bk.start_time BETWEEN %s AND %s AND bk.status IN ('Confirmed', 'Completed')
                GROUP BY f.facility_id, f.name, b.name, f.type
                ORDER BY total_hours DESC
                LIMIT 5
            """
            facilities_data = execute_query(facilities_query, (self.user_id, start_date, end_date))

            if facilities_data:
                self.my_top_facilities_table.setRowCount(len(facilities_data))
                for i, facility in enumerate(facilities_data):
                    self.my_top_facilities_table.setItem(i, 0, QTableWidgetItem(facility['name']))
                    self.my_top_facilities_table.setItem(i, 1, QTableWidgetItem(facility['building_name']))
                    self.my_top_facilities_table.setItem(i, 2, QTableWidgetItem(facility['type']))
                    self.my_top_facilities_table.setItem(i, 3, QTableWidgetItem(f"{float(facility['total_hours'] or 0):.1f} hrs"))
            else:
                self.my_top_facilities_table.setRowCount(0)
                  
        except Exception as e:
            print(f"Error refreshing my analytics: {e}")
            self.show_error_message("Error", f"Failed to load your usage data: {str(e)}")

    def show_styled_message_box(self, icon, title, text, buttons=QMessageBox.StandardButton.Ok):
        """Show a styled message box that matches the app theme"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)

        # Apply light theme styling
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        return msg_box.exec()

    def show_info_message(self, title, text):
        """Show styled information message"""
        return self.show_styled_message_box(QMessageBox.Icon.Information, title, text)

    def show_warning_message(self, title, text):
        """Show styled warning message"""
        return self.show_styled_message_box(QMessageBox.Icon.Warning, title, text)

    def show_error_message(self, title, text):
        """Show styled error message"""
        return self.show_styled_message_box(QMessageBox.Icon.Critical, title, text)

    def show_question_message(self, title, text):
        """Show styled question message with Yes/No buttons"""
        return self.show_styled_message_box(
            QMessageBox.Icon.Question,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

    def show_dashboard(self):
        self.content_area.setCurrentWidget(self.dashboard_page)
        self.load_dashboard_stats() # Refresh dashboard stats

    def manage_my_bookings(self): # New slot
        self.content_area.setCurrentWidget(self.my_bookings_page)
        self.load_all_my_bookings() # Refresh bookings when tab is visited

    def book_facilities(self): # New slot
        self.content_area.setCurrentWidget(self.book_facilities_page)
        self.load_facilities_for_booking() # Refresh facilities when tab is visited

    def show_profile_page(self): # New slot
        self.content_area.setCurrentWidget(self.profile_page)
        # Profile data should be already loaded by user object, but email can be updated.

    def view_my_usage_reports(self): # New slot
        self.content_area.setCurrentWidget(self.my_usage_reports_page)
        self.refresh_my_analytics() # Refresh analytics data when reports page is viewed

    def logout(self):
        reply = self.show_question_message(
            "Confirm Logout",
            "Are you sure you want to logout?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def load_dashboard_stats(self): 
        """Load real-time statistics for the dashboard for the logged-in user"""
        try:
            # My Upcoming Bookings
            upcoming_bookings = execute_query("""
                SELECT COUNT(*) as count
                FROM bookings
                WHERE user_id = %s
                  AND start_time >= NOW()
                  AND status = 'Confirmed'
            """, (self.user_id,))

            upcoming_count = upcoming_bookings[0]['count'] if upcoming_bookings else 0
            self.stat_cards["upcoming_bookings"]["widget"].setText(str(upcoming_count))

            # My Past Bookings (Completed or Confirmed but end_time < now)
            past_bookings = execute_query("""
                SELECT COUNT(*) as count
                FROM bookings
                WHERE user_id = %s
                  AND end_time < NOW()
                  AND status IN ('Confirmed', 'Completed')
            """, (self.user_id,))

            past_count = past_bookings[0]['count'] if past_bookings else 0
            self.stat_cards["past_bookings"]["widget"].setText(str(past_count))

            # My Total Booked Hours
            total_booked_hours = execute_query("""
                SELECT SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)) / 60 as total
                FROM bookings
                WHERE user_id = %s
                  AND status IN ('Confirmed', 'Completed')
            """, (self.user_id,))

            total_hours_amount = total_booked_hours[0]['total'] if total_booked_hours and total_booked_hours[0]['total'] else 0
            self.stat_cards["total_booking_hours"]["widget"].setText(f"{float(total_hours_amount):.1f} hrs")

            # Total Facilities Available (all bookable facilities for any role)
            facilities_available = execute_query("SELECT COUNT(*) as count FROM facilities WHERE is_bookable = TRUE")
            available_count = facilities_available[0]['count'] if facilities_available else 0
            self.stat_cards["facilities_available"]["widget"].setText(str(available_count))

            # Recent bookings (last 5)
            self.recent_bookings_table.setRowCount(0)

            # Booking Reminders (Next 24 hours or your custom logic)
            booking_reminders = execute_query("""
                SELECT COUNT(*) as count
                FROM bookings
                WHERE user_id = %s
                AND start_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 1 DAY)
                AND status = 'Confirmed'
            """, (self.user_id,))

            reminder_count = booking_reminders[0]['count'] if booking_reminders else 0
            self.stat_cards["booking_reminders"]["widget"].setText(str(reminder_count))

            # ✅ Show reminder popup only once
            if not self.reminder_popup_shown:
                def show_reminder_popup():
                    if reminder_count > 0:
                        msg = QMessageBox(self)
                        msg.setWindowTitle("Booking Reminder")
                        msg.setText(f"🔔 You have {reminder_count} upcoming booking reminder(s) today.")
                        msg.setStyleSheet("QLabel { color: white; font-size: 11pt; }")
                        msg.exec()
                    else:
                        msg = QMessageBox(self)
                        msg.setWindowTitle("No Reminders")
                        msg.setText("✅ You have no booking reminders for today.")
                        msg.setStyleSheet("QLabel { color: white; font-size: 11pt; }")
                        msg.exec()
                    self.reminder_popup_shown = True  # ✅ Set flag after showing

                QTimer.singleShot(500, show_reminder_popup)


            recent_bookings = execute_query("""
                SELECT bk.booking_id, bk.booking_number, f.name as facility_name, bu.name as building_name,
                       bk.start_time, bk.end_time, bk.status
                FROM bookings bk
                JOIN facilities f ON bk.facility_id = f.facility_id
                JOIN buildings bu ON f.building_id = bu.building_id
                WHERE bk.user_id = %s
                ORDER BY bk.created_at DESC
                LIMIT 5
            """, (self.user_id,))

            if not recent_bookings:
                self.recent_bookings_table.setRowCount(1)
                no_bookings = QTableWidgetItem("No recent bookings found")
                no_bookings.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_bookings_table.setSpan(0, 0, 1, 5)
                self.recent_bookings_table.setItem(0, 0, no_bookings)
                return

            self.recent_bookings_table.setRowCount(len(recent_bookings))

            for i, booking in enumerate(recent_bookings):
                booking_display = booking.get('booking_number', f"#{booking['booking_id']}")
                
                booking_number_item = QTableWidgetItem(booking_display)
                
                facility_name_item = QTableWidgetItem(booking['facility_name'])
                building_name_item = QTableWidgetItem(booking['building_name'])
                
                time_slot_str = f"{booking['start_time'].strftime('%m/%d %H:%M')} - {booking['end_time'].strftime('%H:%M')}"
                time_slot_item = QTableWidgetItem(time_slot_str)
                
                status_item = QTableWidgetItem(booking['status'])
                if booking['status'] == 'Confirmed':
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                elif booking['status'] == 'Cancelled':
                    status_item.setForeground(Qt.GlobalColor.red)
                elif booking['status'] == 'Pending Approval':
                    status_item.setForeground(Qt.GlobalColor.darkYellow)
                elif booking['status'] == 'Completed':
                    status_item.setForeground(Qt.GlobalColor.blue)

                self.recent_bookings_table.setItem(i, 0, booking_number_item)
                self.recent_bookings_table.setItem(i, 1, facility_name_item)
                self.recent_bookings_table.setItem(i, 2, building_name_item)
                self.recent_bookings_table.setItem(i, 3, time_slot_item)
                self.recent_bookings_table.setItem(i, 4, status_item)

        except Exception as e:
            print(f"Error loading dashboard stats: {e}")
            self.show_error_message("Error", f"Failed to load dashboard statistics: {str(e)}")


    def auto_refresh(self):
        """Automatically refresh data based on current page"""
        try:
            if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
                return
            
            current_widget = self.content_area.currentWidget()

            # Refresh dashboard stats
            if current_widget == self.dashboard_page:
                if not hasattr(self, '_dashboard_refresh_counter'): self._dashboard_refresh_counter = 0
                self._dashboard_refresh_counter += 1
                if self._dashboard_refresh_counter >= 10: # Every 5 seconds
                    self._dashboard_refresh_counter = 0
                    self.load_dashboard_stats()

            # Refresh my bookings page (upcoming bookings might change status to past)
            elif current_widget == self.my_bookings_page:
                if not hasattr(self, '_bookings_refresh_counter'): self._bookings_refresh_counter = 0
                self._bookings_refresh_counter += 1
                if self._bookings_refresh_counter >= 5: # Every 2.5 seconds
                    self._bookings_refresh_counter = 0
                    self.load_all_my_bookings() # Re-evaluate upcoming/past

            # Refresh book facilities page (availability might change)
            elif current_widget == self.book_facilities_page:
                if not hasattr(self, '_facilities_refresh_counter'): self._facilities_refresh_counter = 0
                self._facilities_refresh_counter += 1
                if self._facilities_refresh_counter >= 10: # Every 5 seconds
                    self._facilities_refresh_counter = 0
                    self.load_facilities_for_booking()

            # Refresh personal usage reports
            elif current_widget == self.my_usage_reports_page:
                if not hasattr(self, '_analytics_refresh_counter'): self._analytics_refresh_counter = 0
                self._analytics_refresh_counter += 1
                if self._analytics_refresh_counter >= 10: # Every 5 seconds
                    self._analytics_refresh_counter = 0
                    self.refresh_my_analytics()

        except Exception as e:
            # Silent exception handling for auto-refresh
            print(f"Auto-refresh error in faculty dashboard: {e}")

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


# --- New Dialogs for Faculty ---
class BookingDialog(QDialog):
    def __init__(self, parent=None, user_id=None, facility=None, selected_date=None):
        super().__init__(parent)
        self.user_id = user_id
        self.facility = facility
        self.selected_date = selected_date if selected_date else datetime.date.today()

        self.setWindowTitle(f"Book: {facility['name']} ({facility['building_name']})")
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; color: #2c3e50; }
            QLabel { color: #2c3e50; font-size: 12px; }
            QDateTimeEdit, QComboBox, QTextEdit { background-color: white; color: #2c3e50; border: 1px solid #ddd; border-radius: 4px; padding: 5px; min-height: 25px; }
            QDateTimeEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
            QTableWidget { background-color: white; border: 1px solid #ddd; }
            QHeaderView::section { background-color: #eee; color: #2c3e50; padding: 5px; }
            QTableWidget::item:selected { background-color: #3498db; color: white; }
        """)
        self.initUI()
        self.load_availability()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Facility Info
        info_group = QGroupBox("Facility Information")
        info_layout = QFormLayout(info_group)
        info_layout.addRow("Facility:", QLabel(self.facility['name']))
        info_layout.addRow("Building:", QLabel(self.facility['building_name']))
        info_layout.addRow("Type:", QLabel(self.facility['type']))
        info_layout.addRow("Capacity:", QLabel(str(self.facility['capacity'])))
        layout.addWidget(info_group)

        # Booking Details Form
        booking_group = QGroupBox("Booking Details")
        booking_layout = QFormLayout(booking_group)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(self.selected_date)
        self.date_edit.dateChanged.connect(self.load_availability)
        booking_layout.addRow("Date:", self.date_edit)

        self.start_time_combo = QComboBox()
        self.end_time_combo = QComboBox()
        # Populate these from load_availability based on free slots
        booking_layout.addRow("Start Time:", self.start_time_combo)
        booking_layout.addRow("End Time:", self.end_time_combo)

        self.purpose_input = QTextEdit()
        self.purpose_input.setPlaceholderText("Purpose of booking (e.g., Lecture, Meeting, Study Session)")
        self.purpose_input.setFixedHeight(60)
        booking_layout.addRow("Purpose:", self.purpose_input)
        
        layout.addWidget(booking_group)

        # Availability Display
        self.availability_table = QTableWidget()
        self.availability_table.setColumnCount(2)
        self.availability_table.setHorizontalHeaderLabels(["Start Time", "End Time"])
        self.availability_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.availability_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.availability_table.setAlternatingRowColors(True)
        self.availability_table.setMinimumHeight(150)
        self.availability_table.setToolTip("Green: Available, Red: Booked")
        layout.addWidget(QLabel("Availability for selected date:"))
        layout.addWidget(self.availability_table)

        # Buttons
        button_layout = QHBoxLayout()
        book_btn = QPushButton("Confirm Booking")
        book_btn.clicked.connect(self.submit_booking)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(book_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout) 

    def load_availability(self):
        self.availability_table.setRowCount(0)
        self.start_time_combo.clear()
        self.end_time_combo.clear()

        selected_date_str = self.date_edit.date().toString("yyyy-MM-dd")

        # --- Start background thread for fetching availability ---
        self.worker_thread = QThread()
        self.worker = AvailabilityWorker(self.facility['facility_id'], selected_date_str)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_availability_result)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()


    def handle_availability_result(self, booked_slots):
        self.cached_booked_slots = booked_slots
        selected_date_str = self.date_edit.date().toString("yyyy-MM-dd")

        start_hour = 8
        end_hour = 22
        all_slots = []
        current_time = datetime.datetime.strptime(f"{selected_date_str} {start_hour}:00", "%Y-%m-%d %H:%M")
        while current_time.hour < end_hour or (current_time.hour == end_hour and current_time.minute == 0):
            all_slots.append(current_time)
            current_time += datetime.timedelta(minutes=30)

        self.available_slots = []
        for i in range(len(all_slots) - 1):
            slot_start = all_slots[i]
            slot_end = all_slots[i + 1]
            is_booked = False

            for booked in booked_slots:
                if (booked['start_time'] < slot_end and booked['end_time'] > slot_start):
                    is_booked = True
                    break

            if self.date_edit.date() == QDate.currentDate() and slot_start < datetime.datetime.now():
                is_booked = True

            self.available_slots.append((slot_start, slot_end, not is_booked))

        row_idx = 0
        for start_dt, end_dt, is_available in self.available_slots:
            self.availability_table.insertRow(row_idx)
            start_item = QTableWidgetItem(start_dt.strftime("%H:%M"))
            end_item = QTableWidgetItem(end_dt.strftime("%H:%M"))

            if is_available:
                start_item.setForeground(Qt.GlobalColor.darkGreen)
                end_item.setForeground(Qt.GlobalColor.darkGreen)
                self.start_time_combo.addItem(start_dt.strftime("%H:%M"), start_dt)
                self.end_time_combo.addItem(end_dt.strftime("%H:%M"), end_dt)
            else:
                start_item.setForeground(Qt.GlobalColor.red)
                end_item.setForeground(Qt.GlobalColor.red)

            self.availability_table.setItem(row_idx, 0, start_item)
            self.availability_table.setItem(row_idx, 1, end_item)
            row_idx += 1
        QTimer.singleShot(100, self.update_end_time_options)
        self.start_time_combo.currentIndexChanged.connect(self.update_end_time_options)
        self.update_end_time_options() 
        
    def update_end_time_options(self):
        if not hasattr(self, "available_slots"):
         print("available_slots not loaded yet.")
         return  

        selected_start_dt = self.start_time_combo.currentData()
        self.end_time_combo.clear()
        if not selected_start_dt:
            return

        # Find the rule for this facility type
        # Using db_utils.get_booking_rule
        booking_rule = execute_query("SELECT * FROM booking_rules WHERE facility_type = %s", (self.facility['type'],))
        
        max_duration_minutes = 180 # Default max 3 hours
        if booking_rule and booking_rule[0]:
            max_duration_minutes = booking_rule[0]['max_booking_duration_minutes']
            print(f"Applying booking rule: Max duration {max_duration_minutes} min for {self.facility['type']}")

        # Populate end times based on selected start time and maximum allowed duration
        # Iterate through available slots to find valid end times
        for i in range(self.start_time_combo.count()):
            item_start_dt = self.start_time_combo.itemData(i)
            if item_start_dt == selected_start_dt:
                # Iterate from this start time to find subsequent available slots
                for j in range(i + 1, self.availability_table.rowCount() + 1):
                  if j < self.start_time_combo.count():
                         current_slot_end = self.start_time_combo.itemData(j) # This is not right, needs to read from the original all_slots
                  else: # Handle the very last slot's end time
                        current_slot_end = selected_start_dt + datetime.timedelta(hours=self.facility['capacity'] * 0.5) # Example for labs
                        # This should be dynamic from all_slots logic
                        
                    # Recalculate end time from self.availability_table if possible
                    # Or better, iterate through the original `available_slots` list
                        all_slots = self.get_all_slots_with_availability()  # ✅ store it once
                  for idx, (slot_s, slot_e, is_avail) in enumerate(self.available_slots):
                        if slot_s == selected_start_dt:
                            # From this slot, find contiguous available slots
                            current_end_time = selected_start_dt
                            for k in range(idx, len(self.available_slots)):
                                slot_s_k, slot_e_k, is_avail_k = self.available_slots[k]

                                if is_avail_k and slot_s_k == current_end_time: # Check if this slot is contiguous and available
                                    current_end_time = slot_e_k
                                    duration = (current_end_time - selected_start_dt).total_seconds() / 60
                                    if duration <= max_duration_minutes:
                                        self.end_time_combo.addItem(current_end_time.strftime("%H:%M"), current_end_time)
                                    else:
                                        break
                                else:
                                    break
                            break
                break

    def get_all_slots_with_availability(self):
        """Helper to re-generate the full list of slots and their availability."""
        selected_date_str = self.date_edit.date().toString("yyyy-MM-dd")
        booked_slots = getattr(self, "cached_booked_slots", [])

        start_hour = 8
        end_hour = 22
        all_slots = []
        current_time = datetime.datetime.strptime(f"{selected_date_str} {start_hour}:00", "%Y-%m-%d %H:%M")
        while current_time.hour < end_hour or (current_time.hour == end_hour and current_time.minute == 0):
            all_slots.append(current_time)
            current_time += datetime.timedelta(minutes=30)
        
        full_availability = []
        for i in range(len(all_slots) - 1):
            slot_start = all_slots[i]
            slot_end = all_slots[i+1]
            
            is_booked = False
            for booked in booked_slots:
                if (booked['start_time'] < slot_end and booked['end_time'] > slot_start):
                    is_booked = True
                    break
            if self.date_edit.date() == QDate.currentDate() and slot_start < datetime.datetime.now():
                is_booked = True

            full_availability.append((slot_start, slot_end, not is_booked))
        return full_availability

    def submit_booking(self):
        start_dt = self.start_time_combo.currentData()
        end_dt = self.end_time_combo.currentData()
        
        purpose = self.purpose_input.toPlainText().strip()

        if not (start_dt and end_dt and purpose):
           QMessageBox.warning(self, "Validation Error", "Please select start/end times and enter a purpose.")
           return

        if end_dt <= start_dt:
            QMessageBox.warning(self, "Validation Error", "End time must be after start time.")
            return

        selected_date = self.date_edit.date().toPython()
        start_dt_obj = datetime.datetime.combine(selected_date, start_dt.time())
        end_dt_obj = datetime.datetime.combine(selected_date, end_dt.time())

        # Save booking to database
        
        success = create_booking(
            self.user_id,
            self.facility['facility_id'],
            start_dt_obj,
            end_dt_obj,
            purpose
        )

        if success:
            self.send_email_confirmation()  # ✅ send email
            QMessageBox.information(self, "Success", "Booking confirmed.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Booking failed. Please try again.")



### Add this method inside the BookingDialog class:

    def send_email_confirmation(self):
        try:
            user_email = self.parent().user.email if hasattr(self.parent(), 'user') else None
            if not user_email:
                print("Email not found for user.") 
                return
            
            start_dt_obj = self.start_time_combo.currentData()
            end_dt_obj = self.end_time_combo.currentData()

            sender_email = "nadinwaleedh@gmail.com"  # Replace with actual sender
            sender_password = "lbcq ayfo gmko yrpz"  # Replace with actual password or use secure config

            subject = "Facility Booking Confirmation"
            body = f"""
Dear {self.parent().user.username},

Your booking for {self.facility['name']} ({self.facility['building_name']}) has been confirmed.

Date: {self.date_edit.date().toString("yyyy-MM-dd")}
Start Time: {self.start_time_combo.currentText()}
End Time: {self.end_time_combo.currentText()}
Purpose: {self.purpose_input.toPlainText().strip()}
Regards,
Smart Campus Team
            """

            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = user_email
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
            server.quit()

            print("Email sent successfully to", user_email)

        except Exception as e:
            print("Error sending email:", e)

        
        # Final check for availability before booking (race condition check)
        # This is a critical step
        
        # Check for time slot conflicts before booking
        current_booked_slots = get_facility_availability(
        self.facility['facility_id'],
        self.date_edit.date().toString("yyyy-MM-dd")
        )

        for booked in current_booked_slots:
            if (booked['start_time'] < end_dt_obj and booked['end_time'] > start_dt_obj):
                self.load_availability()  # Refresh UI
                return  # Booking conflict found — exit

        try:
            # Check booking rules
            booking_rule = execute_query("SELECT * FROM booking_rules WHERE facility_type = %s", (self.facility['type'],))

            if booking_rule and booking_rule[0]:
                rule = booking_rule[0]

                # Max duration
                duration_minutes = (end_dt_obj - start_dt_obj).total_seconds() / 60
                if duration_minutes > rule['max_booking_duration_minutes']:
                    return  # Violates max duration

                # Min advance notice
                min_advance_timedelta = datetime.timedelta(hours=rule['min_booking_advance_hours'])
                if datetime.datetime.now() + min_advance_timedelta > start_dt_obj:
                    return  # Violates advance notice

                # Max concurrent
                if rule['max_concurrent_bookings_per_user'] > 0:
                    user_role = execute_query("SELECT role FROM users WHERE user_id = %s", (self.user_id,))
                    if user_role and user_role[0]['role'] in rule['applies_to_roles'].split(','):
                        current_active_bookings = execute_query("""
                            SELECT COUNT(*) as count FROM bookings
                            WHERE user_id = %s AND status = 'Confirmed' AND end_time > NOW()
                        """, (self.user_id,))
                        if current_active_bookings and current_active_bookings[0]['count'] >= rule['max_concurrent_bookings_per_user']:
                            return  # Too many concurrent bookings

            # Get purpose input
            purpose = self.purpose_input.toPlainText().strip()

            # Try to book
            booking_id = create_booking(self.user_id, self.facility['facility_id'], start_dt_obj, end_dt_obj, purpose)

            # Handle result — no popups
            if booking_id is not None and isinstance(booking_id, int) and booking_id > 0:
                self.accept()  # Close dialog if success
            else:
                pass  # Booking failed — silently ignore or handle differently

        except Exception as e:
            print(f"Error during booking: {e}")
