from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem, QStackedWidget, QMessageBox,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QComboBox, QHeaderView, QSlider, QGroupBox, QTextEdit,QTabWidget,
    QSpinBox, QProgressBar, QMenu, QCheckBox, QRadioButton, QDateEdit, QDateTimeEdit
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QDate, QDateTime
from PySide6.QtGui import QFont, QIcon, QPixmap, QCursor, QColor, QPainter  
import os
import datetime # Import the datetime module explicitly
import re # Import the re module for email validation
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Import relevant SCNFBS DB functions
from db_utils import execute_query, get_facility_availability, create_booking, cancel_booking, get_user_bookings, search_buildings, search_facilities

# --- New Dialog for Booking (reused from FacultyDashboard) ---
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
        self.purpose_input.setPlaceholderText("Purpose of booking (e.g., Group Study, Project Work)")
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
        self.availability_table.setStyleSheet("QTableWidget { background-color: #f9f9f9; color: black; }")
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

        def on_result(available_slots):
            self.available_slots = available_slots
            for row_idx, (start_dt, end_dt, is_available) in enumerate(available_slots):
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

            self.update_end_time_options()

        # Run in background thread
        worker = LoadAvailabilityWorker(self.facility['facility_id'], selected_date_str, on_result)
        QThreadPool.globalInstance().start(worker)


    def update_end_time_options(self):
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
                # From this slot, find contiguous available slots
                current_end_time = selected_start_dt
                for k in range(i, self.availability_table.rowCount()):
                    # Re-retrieve full availability for robust check
                    all_slots_with_avail = self.get_all_slots_with_availability()
                    if k >= len(all_slots_with_avail): # Prevent index out of range
                        break
                    
                    slot_s_k, slot_e_k, is_avail_k = all_slots_with_avail[k]
                    
                    # Check if this slot is contiguous, available, and within max duration
                    if is_avail_k and slot_s_k == current_end_time:
                        current_end_time = slot_e_k
                        duration = (current_end_time - selected_start_dt).total_seconds() / 60
                        if duration <= max_duration_minutes:
                            self.end_time_combo.addItem(current_end_time.strftime("%H:%M"), current_end_time)
                        else:
                            break
                    else:
                        break
                break

    def get_all_slots_with_availability(self):
        """Helper to re-generate the full list of slots and their availability."""
        selected_date_str = self.date_edit.date().toString("yyyy-MM-dd")
        booked_slots = get_facility_availability(self.facility['facility_id'], selected_date_str)

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
        start_dt_obj = self.start_time_combo.currentData()
        end_dt_obj = self.end_time_combo.currentData()
        purpose = self.purpose_input.toPlainText().strip()

        if not start_dt_obj or not end_dt_obj or not purpose:
            QMessageBox.warning(self, "Validation Error", "Please select start/end times and enter a purpose.")
            return
        
        if start_dt_obj >= end_dt_obj:
            QMessageBox.warning(self, "Validation Error", "End time must be after start time.")
            return

        if self.date_edit.date() == QDate.currentDate() and start_dt_obj < datetime.datetime.now():
            QMessageBox.warning(self, "Validation Error", "Cannot book in the past for today's date.")
            return
        
        # Final check for availability before booking (race condition check)
        
        current_booked_slots = get_facility_availability(self.facility['facility_id'], self.date_edit.date().toString("yyyy-MM-dd"))
        for booked in current_booked_slots:
            if (booked['start_time'] < end_dt_obj and booked['end_time'] > start_dt_obj):
                QMessageBox.critical(self, "Booking Conflict", "The selected time slot is no longer available. Please refresh and try again.")
                self.load_availability() # Refresh UI
                return

        try:
            # Check booking rules (max duration, min advance notice, max concurrent)
            booking_rule = execute_query("SELECT * FROM booking_rules WHERE facility_type = %s", (self.facility['type'],))
            
            if booking_rule and booking_rule[0]:
                rule = booking_rule[0]
                
                # Max duration check
                duration_minutes = (end_dt_obj - start_dt_obj).total_seconds() / 60
                if duration_minutes > rule['max_booking_duration_minutes']:
                    QMessageBox.warning(self, "Booking Rule Violation", 
                                        f"Maximum booking duration for {self.facility['type']} is {rule['max_booking_duration_minutes']} minutes.")
                    return
                
                # Min advance notice check
                min_advance_timedelta = datetime.timedelta(hours=rule['min_booking_advance_hours'])
                if datetime.datetime.now() + min_advance_timedelta > start_dt_obj:
                    QMessageBox.warning(self, "Booking Rule Violation",
                                        f"Bookings for {self.facility['type']} require at least {rule['min_booking_advance_hours']} hours advance notice.")
                    return
                
                # Max concurrent bookings per user (only for roles that have this limit)
                if rule['max_concurrent_bookings_per_user'] > 0:
                    user_role = execute_query("SELECT role FROM users WHERE user_id = %s", (self.user_id,))
                    if user_role and user_role[0]['role'] in rule['applies_to_roles'].split(','):
                        
                        current_active_bookings = execute_query("""
                            SELECT COUNT(*) as count FROM bookings
                            WHERE user_id = %s AND status = 'Confirmed' AND end_time > NOW()
                        """, (self.user_id,))
                        
                        if current_active_bookings and current_active_bookings[0]['count'] >= rule['max_concurrent_bookings_per_user']:
                            QMessageBox.warning(self, "Booking Rule Violation",
                                                f"You can only have {rule['max_concurrent_bookings_per_user']} concurrent confirmed bookings.")
                            return
            
            # Use the create_booking function from db_utils
            booking_id = create_booking(self.user_id, self.facility['facility_id'], start_dt_obj, end_dt_obj, purpose)

            if booking_id:
                popup_message = f"Dear Student,\n\nYour booking for {self.facility['name']} has been successfully confirmed.\n\nRegards,\nSmart Campus Team"
    
                QMessageBox.information(self, "📧 Email", popup_message)
                self.send_email_confirmation(popup_message)
                self.accept()
            else:
              QMessageBox.information(
    self,
    "📧 Email",
    f"Dear Student,\n\nYour booking for {self.facility['name']} failed.\n\nRegards,\nSmart Campus Team")
        except Exception as e:
            QMessageBox.critical(self, "📧 Email", f"An error occurred during booking: {str(e)}")
            print(f"Error during booking: {e}")

    def send_email_confirmation(self, popup_message):
        try:
            user_email = self.parent().user.email if hasattr(self.parent(), 'user') else None
            if not user_email:
                print("Email not found for user.")
                return

            sender_email = "place your email id"  # ✅ Your working email
            sender_password = "plCace your app password"            # ✅ Your app password

            start_time = self.start_time_combo.currentText()
            end_time = self.end_time_combo.currentText()
            purpose = self.purpose_input.toPlainText().strip()
            booking_date = self.date_edit.date().toString("yyyy-MM-dd")

            subject = "Facility Booking Confirmation"
            body = f"""{popup_message}

    Full Booking Details:

    Date: {booking_date}
    Start Time: {start_time}
    End Time: {end_time}
    Purpose: {purpose}
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


# --- Student Dashboard ---
class StudentDashboard(QWidget):
    logout_requested = Signal()
    
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.user_id = user.user_id # Access user ID directly from the User object
        self.reminder_popup_shown = False #Added by teacher
        
        # Initialize booking layouts dictionary for My Bookings page
        self.booking_layouts = {
            'Upcoming': None,
            'Past': None,
            'Cancelled': None
        }
        
        # Set up auto-refresh timer for real-time updates
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(500)  # Refresh every 0.5 seconds
        
        self.initUI()
        
        # Load initial data
        self.load_dashboard_stats()
        self.load_facilities_for_booking() # Load facilities when dashboard starts
    
    def initUI(self):
        self.setWindowTitle("Smart Campus - Student Dashboard") # Updated Title
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Set zero margins
        main_layout.setSpacing(0)  # Remove spacing
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(250)
        sidebar.setMinimumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 10)  # Add proper padding
        
        # User info section
        user_info = QFrame()
        user_info.setObjectName("user-info")
        user_info_layout = QVBoxLayout(user_info)
        user_info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile pic - can be dynamic later
        profile_pic = QLabel()
        profile_pic.setObjectName("profile-pic")
        profile_pic.setPixmap(QPixmap("assets/img/student-avatar.png").scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        profile_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome_label = QLabel(f"Welcome, {self.user.username}")
        welcome_label.setObjectName("welcome-label")
        welcome_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        
        user_role_label = QLabel(self.user.role.name.capitalize())
        user_role_label.setObjectName("user-role")

        user_info_layout.addWidget(profile_pic)
        user_info_layout.addWidget(welcome_label)
        user_info_layout.addWidget(user_role_label)
        sidebar_layout.addWidget(user_info)
        
        # Navigation buttons - Updated for SCNFBS Student
        nav_buttons = [
            {"text": "Dashboard", "icon": "📊", "slot": self.show_dashboard},
            {"text": "Find Facilities", "icon": "📍", "slot": self.find_facilities}, # New
            {"text": "My Bookings", "icon": "📅", "slot": self.my_bookings}, # Renamed from Orders
            {"text": "Campus Map", "icon": "🗺️", "slot": self.show_campus_map}, # New (placeholder)
            {"text": "My Profile", "icon": "👤", "slot": self.profile},
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
        
        # Create pages
        self.dashboard_page = self.create_dashboard_page()
        self.find_facilities_page = self.create_find_facilities_page() # New
        self.my_bookings_page = self.create_my_bookings_page() # New
        self.campus_map_page = self.create_campus_map_page() # New (placeholder)
        self.profile_page = self.create_profile_page()
        
        # Add pages to content area
        self.content_area.addWidget(self.dashboard_page)
        self.content_area.addWidget(self.find_facilities_page)
        self.content_area.addWidget(self.my_bookings_page)
        self.content_area.addWidget(self.campus_map_page)
        self.content_area.addWidget(self.profile_page)
        
        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_area)
        
        # Apply styles (adjust as needed for SCNFBS theme)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2c3e50; 
            }
            #sidebar {
                background-color: #2c3e50;
                border-radius: 0px;
                padding: 10px;
                color: white;
            }
            #user-info {
                border-bottom: 1px solid #34495e;
                padding: 15px;
                margin-bottom: 15px;
                background-color: #243342;
                border-radius: 8px;
            }
            #profile-pic {
                background-color: transparent;
                padding: 0;
                margin: 0;
            }
            #welcome-label {
                color: white;
                background-color: transparent;
            }
            #user-role {
                color: #3498db;
                font-size: 14px;
            }
            #nav-button {
                text-align: left;
                background-color: #34495e;
                border-radius: 4px;
                color: white;
                font-size: 14px;
                padding: 12px;
                margin: 5px 0;
            }
            #nav-button:hover {
                background-color: #3498db;
            }
            #logout-button {
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
                padding: 12px;
            }
            #logout-button:hover {
                background-color: #c0392b;
            }
            
            /* General Action Button */
            #action-button {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            #action-button:hover {
                background-color: #2980b9;
            }
            
            /* Table Styles */
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
            
            /* Input and ComboBox */
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QDateEdit, QDateTimeEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
                color: #2c3e50;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QDateEdit:focus, QDateTimeEdit:focus {
                border: 1px solid #3498db;
            }
            
            /* Group Box */
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 1.5em;
                padding-top: 10px;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            
            /* Specific Card Styles */
            #stat-card {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                min-height: 100px;
                border: 1px solid #e0e0e0;
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
            
            #delete-button {
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            #delete-button:hover {
                background-color: #c0392b;
            }
        """)
        
        # Start with dashboard
        self.content_area.setCurrentWidget(self.dashboard_page)
    
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Header
        header = QLabel("Student Dashboard")
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
            "total_facilities": {"title": "Total Facilities", "value": "0", "icon": "📍", "widget": None},
            "reminders": {"title": "Reminders", "value": "0", "icon": "🔔", "widget": None}  # ✅ Added this
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
        layout.addWidget(recent_bookings_label)
        layout.addWidget(self.recent_bookings_table)
        
        return page
    
    def create_find_facilities_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Find & Book Facilities")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()

        # Search and filter for facilities
        filter_group = QGroupBox("Filter Facilities")
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

        self.booking_date_selector = QDateEdit()
        self.booking_date_selector.setCalendarPopup(True)
        self.booking_date_selector.setDate(QDate.currentDate())
        filter_layout.addRow("Select Date:", self.booking_date_selector)
        

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

        # Date range for bookings
        date_label = QLabel("Date:")
        self.bookings_start_date = QDateEdit()
        self.bookings_start_date.setCalendarPopup(True)
        self.bookings_start_date.setDate(QDate.currentDate().addMonths(-1))

        to_label = QLabel("to")

        self.bookings_end_date = QDateEdit()
        self.bookings_end_date.setCalendarPopup(True)
        self.bookings_end_date.setDate(QDate.currentDate().addMonths(3))

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

        try:
            my_bookings = get_user_bookings(self.user_id) # Using the db_utils function

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
                self.show_info_message("📧 Email", f"Dear Student,\n\nYour booking has been cancelled.\n\n– Smart Campus")
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
            # Query directly for this user with search filters
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

    
    def get_directions(self):
        start_point = self.start_location_input.text().strip()
        end_point = self.end_location_input.text().strip()
        accessible_only = self.accessible_path_checkbox.isChecked()

        if not start_point or not end_point:
            self.show_warning_message("Input Error", "Please enter both start and end locations.")
            return
        
        self.directions_output.clear()
        self.directions_output.setText("Searching for directions...")

        try:
            if accessible_only:
                paths = execute_query(
                    "SELECT * FROM map_paths WHERE start_point LIKE %s AND end_point LIKE %s AND is_accessible = TRUE ORDER BY distance_meters ASC",
                    (f"%{start_point}%", f"%{end_point}%")
                )
            else:
                paths = execute_query(
                    "SELECT * FROM map_paths WHERE start_point LIKE %s AND end_point LIKE %s ORDER BY distance_meters ASC",
                    (f"%{start_point}%", f"%{end_point}%")
                )

            if paths:
                directions_text = "Directions Found:\n\n"
                for i, path in enumerate(paths):
                    directions_text += f"--- Route {i+1} ---\n"
                    directions_text += f"From: {path['start_point']}\n"
                    directions_text += f"To: {path['end_point']}\n"
                    directions_text += f"Distance: {path['distance_meters']:.1f} meters\n"
                    directions_text += f"Estimated Duration: {path['duration_minutes']:.1f} minutes\n"
                    directions_text += f"Accessible: {'Yes' if path['is_accessible'] else 'No'}\n"
                    directions_text += f"Instructions: {path['description'] or 'Follow campus signs.'}\n\n"
                self.directions_output.setText(directions_text)
            else:
                self.directions_output.setText("No direct paths found between the specified locations. Try different keywords.")
        except Exception as e:
            self.directions_output.setText(f"Error fetching directions: {str(e)}")
            print(f"Error getting directions: {e}")

    
    def create_profile_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Header
        header = QLabel("My Profile")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setFont(QFont("Arial", 24))
        
        # Profile form container
        form_container = QFrame()
        form_container.setObjectName("profile-card")
        form_layout = QVBoxLayout(form_container)
        
        # Input fields
        input_layout = QFormLayout()
        
        self.profile_username = QLineEdit(self.user.username)
        self.profile_username.setReadOnly(True) # Username usually not changeable
        self.profile_username.setStyleSheet("background-color: #f0f0f0; color: #555;")

        self.profile_email = QLineEdit(self.user.email)
        self.profile_email.setPlaceholderText("Enter your email")
        
        self.profile_role = QLineEdit(self.user.role.name.capitalize())
        self.profile_role.setReadOnly(True)
        self.profile_role.setStyleSheet("background-color: #f0f0f0; color: #555;")
        
        # Add fields to form
        input_layout.addRow("Username:", self.profile_username)
        input_layout.addRow("Email:", self.profile_email)
        input_layout.addRow("Role:", self.profile_role)
        
        # Save button for email
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Update Email")
        save_btn.setObjectName("action-button")
        save_btn.clicked.connect(self.save_profile)

        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        
        # Add all to container
        form_layout.addLayout(input_layout)
        form_layout.addLayout(button_layout) # Add the button layout to form_layout
        
        # Load customer profile data (which now means just user email)
        self.load_user_profile() # Renamed function
        
        # Add to main layout
        layout.addWidget(header)
        layout.addWidget(form_container)
        layout.addStretch()
        
        return page

    def load_user_profile(self):
        """Load user profile information from database (just email from users table)"""
        try:
            user_result = execute_query(
                "SELECT email FROM users WHERE user_id = %s",
                (self.user.user_id,)
            )
            
            if user_result and hasattr(self, 'profile_email'):
                self.profile_email.setText(user_result[0].get('email', ''))
        except Exception as e:
            print(f"Error loading user profile: {e}")

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
            query = "UPDATE users SET email = %s WHERE user_id = %s"
            result = execute_query(query, (new_email, self.user_id), fetch=False)

            if result is not None:
                self.user.email = new_email # Update the user object in memory
                self.show_info_message("Success", "Your profile has been updated successfully!")
            else:
                self.show_error_message("Error", "Failed to update profile.")
        except Exception as e:
            self.show_error_message("Error", f"An error occurred: {str(e)}")
            print(f"Profile save error: {e}")
    
    def show_dashboard(self):
        self.content_area.setCurrentWidget(self.dashboard_page)
        self.load_dashboard_stats() # Refresh dashboard stats
    
    def find_facilities(self): # New slot
        self.content_area.setCurrentWidget(self.find_facilities_page)
        self.load_facilities_for_booking() # Refresh facilities when tab is visited

    def my_bookings(self): # Renamed slot
        self.content_area.setCurrentWidget(self.my_bookings_page)
        self.load_all_my_bookings() # Refresh bookings when tab is visited
    
    def show_campus_map(self): # New slot
        self.content_area.setCurrentWidget(self.campus_map_page)
        # No specific load needed here unless map data is dynamically loaded

    def profile(self): # Renamed slot
        self.content_area.setCurrentWidget(self.profile_page)
        self.load_user_profile() # Refresh profile data

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

            # Total Facilities (all bookable facilities for any role)
            total_facilities = execute_query("SELECT COUNT(*) as count FROM facilities WHERE is_bookable = TRUE")
            total_fac_count = total_facilities[0]['count'] if total_facilities else 0
            self.stat_cards["total_facilities"]["widget"].setText(str(total_fac_count))

            # Booking Reminders - upcoming bookings in next 24 hours(Added by teacher)
            reminder_bookings = execute_query("""
                SELECT COUNT(*) as count
                FROM bookings
                WHERE user_id = %s
                AND start_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 1 DAY)
                AND status = 'Confirmed'
            """, (self.user_id,))

            reminder_count = reminder_bookings[0]['count'] if reminder_bookings else 0
            self.stat_cards["reminders"]["widget"].setText(str(reminder_count))

            if not self.reminder_popup_shown:
                def show_reminder_popup():
                    if reminder_count > 0:
                        msg = QMessageBox(self)
                        msg.setWindowTitle("Booking Reminder")
                        msg.setText(f"🔔 You have {reminder_count} upcoming booking(s) within 24 hours.")
                    else:
                        msg = QMessageBox(self)
                        msg.setWindowTitle("No Reminders")
                        msg.setText("✅ You have no upcoming bookings today.")
                    msg.setStyleSheet("QLabel { color: white; font-size: 13pt; }")
                    msg.exec()
                    self.reminder_popup_shown = True  # ✅ Set flag after showing

                QTimer.singleShot(500, show_reminder_popup)


            # Recent bookings (last 5)
            
            self.recent_bookings_table.setRowCount(0)

            recent_bookings = execute_query("""
                SELECT bk.booking_id, bk.booking_number, f.name as facility_name, bu.name as building_name,
                       bk.start_time, bk.end_time, bk.status
                FROM bookings bk
                JOIN users u ON bk.user_id = u.user_id
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
            # Skip refresh if mouse button is pressed to prevent click interference
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import Qt
            
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

            # Refresh find facilities page (availability might change)
            elif current_widget == self.find_facilities_page:
                if not hasattr(self, '_facilities_refresh_counter'): self._facilities_refresh_counter = 0
                self._facilities_refresh_counter += 1
                if self._facilities_refresh_counter >= 10: # Every 5 seconds
                    self._facilities_refresh_counter = 0
                    self.load_facilities_for_booking() # Reload facilities based on current filters


        except Exception as e:
            # Silent exception handling for auto-refresh
            print(f"Auto-refresh error in student dashboard: {e}")
            # Don't show error to user since this runs automatically

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
    
    # --- Helper Message Box Functions (reused from FacultyDashboard) ---
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
    
    def create_campus_map_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Campus Map & Navigation")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 24))

        # Load base map image
        map_image_path = "map_assets/mapo.png"
        base_pixmap = QPixmap(map_image_path)

        if base_pixmap.isNull():
            map_label = QLabel("❌ Map image not found at: " + map_image_path)
            map_label.setStyleSheet("color: red; font-size: 14px;")
            map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(header)
            layout.addWidget(map_label)
            return page

        # Draw icons on top of the map image
        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Arial", 24)
        painter.setFont(font)

        # Adjust these (x, y) coordinates based on your actual map layout
        painter.drawText(60, 50, "🚪")    # Entry
        painter.drawText(200, 100, "🛗")   # Elevator
        painter.drawText(80, 210, "♿")   # Accessible
        painter.drawText(500, 390, "📍")  # Destination

        painter.end()

        map_label = QLabel()
        map_label.setPixmap(base_pixmap.scaled(800, 500, Qt.AspectRatioMode.KeepAspectRatio))
        map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Directions Form
        nav_group = QGroupBox("Get Directions")
        nav_layout = QFormLayout(nav_group)

        self.start_location_input = QLineEdit()
        self.start_location_input.setPlaceholderText("e.g., Main Entrance")
        nav_layout.addRow("From:", self.start_location_input)

        self.end_location_input = QLineEdit()
        self.end_location_input.setPlaceholderText("e.g., Study Room 101")
        nav_layout.addRow("To:", self.end_location_input)

        self.accessible_path_checkbox = QCheckBox("Show Accessible Paths Only")
        nav_layout.addRow("Options:", self.accessible_path_checkbox)

        get_directions_btn = QPushButton("Get Directions")
        get_directions_btn.clicked.connect(self.show_static_directions)
        nav_layout.addRow("", get_directions_btn)

        # Text instructions
        self.directions_output = QTextEdit()
        self.directions_output.setReadOnly(True)
        self.directions_output.setText("🔍 Directions will appear here.")
        self.directions_output.setMinimumHeight(120)

        layout.addWidget(header)
        layout.addWidget(map_label)
        layout.addWidget(nav_group)
        layout.addWidget(self.directions_output)

        return page


    def show_static_directions(self):
        start = self.start_location_input.text().strip().lower()
        end = self.end_location_input.text().strip().lower()
        accessible = self.accessible_path_checkbox.isChecked()

        routes = {
            ("main library", "engineering block a"): {
                "distance": "750.0 meters",
                "duration": "9.5 minutes",
                "accessible": "Yes",
                "instructions": "Walkway between Main Library and Engineering Block A"
            },
            ("building a", "library"): {
                "distance": "500.0 meters",
                "duration": "6 minutes",
                "accessible": "Yes" if accessible else "No",
                "instructions": "Take elevator in Building A, follow signs to the Library via Building E"
            },
            ("building a", "food court"): {
                "distance": "700.0 meters",
                "duration": "8 minutes",
                "accessible": "Yes" if accessible else "No",
                "instructions": "Walk through Buildings B → C → D → E and reach the Food Court"
            }
        }

        key = (start, end)
        if key in routes:
            route = routes[key]
            output = f"""--- Route ---
    From: {start.title()}
    To: {end.title()}
    Distance: {route['distance']}
    Estimated Duration: {route['duration']}
    Accessible: {route['accessible']}
    Instructions: {route['instructions']}"""
        else:
            output = "⚠️ No route found for this combination.\nTry:\n- Main Library → Engineering Block A\n- Building A → Library"

        self.directions_output.setText(output)
