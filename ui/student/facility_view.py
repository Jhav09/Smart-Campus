from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QFrame, QGridLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QDialog, QFormLayout, QTextEdit, QLineEdit, QDateEdit, QDateTimeEdit, QGroupBox,
)
from PySide6.QtCore import Qt, Signal, QDate, QTime, QDateTime
from PySide6.QtGui import QFont, QIcon, QPixmap,QColor
from PySide6.QtGui import Qmessage 
import datetime # Explicitly import datetime
import re # Explicitly import re

from db_utils import execute_query, get_facility_availability, create_booking # Import relevant SCNFBS DB functions
# Re-import BookingDialog from the student dashboard if it's in a separate file,
# or define it here if it's purely internal to this view.
# For consistency and avoiding circular imports if FacilityView is in a sub-folder,
# let's assume BookingDialog is in student_dashboard or db_utils.
# If you place BookingDialog in a separate file like dialogs/booking_dialog.py,
# you would import it like: from ui.dialogs.booking_dialog import BookingDialog
# For now, I'll include the BookingDialog class directly in this file as a standalone
# component, as it was copied from the FacultyDashboard and is a common pattern.

class BookingDialog(QDialog):
    # This class is duplicated here for self-containment.
    # In a larger project, consider putting common dialogs in a shared 'dialogs' folder.
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
        self.apply_styles()
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
        selected_date_str = self.date_edit.date().toString("yyyy-MM-dd")
        booked_slots = get_facility_availability(self.facility['facility_id'], selected_date_str)

        self.availability_table.setRowCount(0)
        self.start_time_combo.clear()
        self.end_time_combo.clear()

        # Generate all possible 30-minute slots for the day (e.g., 8 AM to 10 PM)
        start_hour = 8
        end_hour = 22 # 10 PM
        all_slots = []
        current_time = datetime.datetime.strptime(f"{selected_date_str} {start_hour}:00", "%Y-%m-%d %H:%M")
        while current_time.hour < end_hour or (current_time.hour == end_hour and current_time.minute == 0):
            all_slots.append(current_time)
            current_time += datetime.timedelta(minutes=30)
        
        # Determine available slots
        available_slots = []
        for i in range(len(all_slots) - 1):
            slot_start = all_slots[i]
            slot_end = all_slots[i+1]
            
            is_booked = False
            for booked in booked_slots:
                # Check for overlap: [booked_start, booked_end] overlaps with [slot_start, slot_end]
                if (booked['start_time'] < slot_end and booked['end_time'] > slot_start):
                    is_booked = True
                    break
            
            # Check if this slot start time is in the past (only for today)
            if self.date_edit.date() == QDate.currentDate() and slot_start < datetime.datetime.now():
                is_booked = True # Treat past slots as unavailable

            available_slots.append((slot_start, slot_end, not is_booked))

        # Populate availability table and time combos
        row_idx = 0
        for start_dt, end_dt, is_available in available_slots:
            self.availability_table.insertRow(row_idx)
            start_item = QTableWidgetItem(start_dt.strftime("%H:%M"))
            end_item = QTableWidgetItem(end_dt.strftime("%H:%M"))
            
            if is_available:
                start_item.setForeground(Qt.GlobalColor.darkGreen)
                end_item.setForeground(Qt.GlobalColor.darkGreen)
                self.start_time_combo.addItem(start_dt.strftime("%H:%M"), start_dt)
                self.end_time_combo.addItem(end_dt.strftime("%H:%M"), end_dt) # Add all end times to allow duration selection
            else:
                start_item.setForeground(Qt.GlobalColor.red)
                end_item.setForeground(Qt.GlobalColor.red)
            
            self.availability_table.setItem(row_idx, 0, start_item)
            self.availability_table.setItem(row_idx, 1, end_item)
            row_idx += 1
            
        # Adjust end time combo after start time is selected
        self.start_time_combo.currentIndexChanged.connect(self.update_end_time_options)
        self.update_end_time_options() # Call initially

    def update_end_time_options(self):
        selected_start_dt = self.start_time_combo.currentData()
        self.end_time_combo.clear()
        if not selected_start_dt:
            return

        # Find the rule for this facility type
        booking_rule = execute_query("SELECT * FROM booking_rules WHERE facility_type = %s", (self.facility['type'],))
        
        max_duration_minutes = 180 # Default max 3 hours
        if booking_rule and booking_rule[0]:
            max_duration_minutes = booking_rule[0]['max_booking_duration_minutes']

        # Populate end times based on selected start time and maximum allowed duration
        for i in range(len(self.start_time_combo)):
            item_start_dt = self.start_time_combo.itemData(i)
            if item_start_dt == selected_start_dt:
                current_end_time = selected_start_dt
                for k in range(i, len(self.get_all_slots_with_availability())):
                    all_slots_with_avail = self.get_all_slots_with_availability()
                    if k >= len(all_slots_with_avail):
                        break
                    
                    slot_s_k, slot_e_k, is_avail_k = all_slots_with_avail[k]
                    
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



class FacilityView(QWidget):
    back_to_facilities = Signal() # Renamed signal

    def __init__(self, user_id, facility_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id # Store user_id to pass to booking dialog
        self.facility_id = facility_id
        self.facility_data = None
        self.load_facility_data()
        self.initUI()

    def load_facility_data(self):
        """Load facility details and its associated building data."""
        result = execute_query(
            """
            SELECT f.*, b.name as building_name, b.address as building_address
            FROM facilities f
            JOIN buildings b ON f.building_id = b.building_id
            WHERE f.facility_id = %s
            """,
            (self.facility_id,)
        )
        if result:
            self.facility_data = result[0]
        else:
            self.facility_data = None # Explicitly set to None if not found

    def initUI(self):
        if not self.facility_data:
            error_layout = QVBoxLayout(self)
            error_label = QLabel("Facility not found or inactive.")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setFont(QFont("Arial", 16))
            error_layout.addWidget(error_label)
            return

        self.setWindowTitle(f"Smart Campus - {self.facility_data['name']}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("facility-header")
        header_layout = QVBoxLayout(header_frame)

        # Back button
        back_btn = QPushButton("← Back to Facilities")
        back_btn.setObjectName("back-button")
        back_btn.clicked.connect(self.back_to_facilities.emit)

        # Facility name and info
        name_label = QLabel(self.facility_data['name'])
        name_label.setObjectName("facility-name")
        name_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))

        # Combined info: Type, Capacity, Building
        info_label = QLabel(
            f"Type: {self.facility_data['type']} • "
            f"Capacity: {self.facility_data['capacity']} • "
            f"Building: {self.facility_data['building_name']}"
        )
        info_label.setObjectName("facility-info")

        description_label = QLabel(self.facility_data['description'] or "No description available.")
        description_label.setObjectName("facility-description")
        description_label.setWordWrap(True)

        location_desc_label = QLabel(f"Location: {self.facility_data.get('location_description', 'N/A')}")
        location_desc_label.setObjectName("facility-location")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(name_label)
        header_layout.addWidget(info_label)
        header_layout.addWidget(description_label)
        header_layout.addWidget(location_desc_label)

        # Availability & Booking Section
        booking_section_label = QLabel("Check Availability & Book")
        booking_section_label.setObjectName("section-header")
        booking_section_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        # Date selector for availability
        date_selection_layout = QHBoxLayout()
        date_selection_layout.addWidget(QLabel("Select Date:"))
        self.booking_date_selector = QDateEdit()
        self.booking_date_selector.setCalendarPopup(True)
        self.booking_date_selector.setDate(QDate.currentDate())
        self.booking_date_selector.dateChanged.connect(self.load_availability_and_times) # Connect to reload
        date_selection_layout.addWidget(self.booking_date_selector)
        date_selection_layout.addStretch()

        # Display for available slots (a simple table or list)
        self.availability_table = QTableWidget()
        self.availability_table.setColumnCount(2)
        self.availability_table.setHorizontalHeaderLabels(["Start Time", "End Time"])
        self.availability_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.availability_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.availability_table.setAlternatingRowColors(True)
        self.availability_table.setMinimumHeight(200)
        
        # Booking button
        book_now_btn = QPushButton("Book This Facility")
        book_now_btn.setObjectName("action-button")
        # Pass current user_id and facility data to the dialog
        book_now_btn.clicked.connect(self.open_booking_dialog)
        
        # Add all widgets to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(booking_section_label)
        main_layout.addLayout(date_selection_layout)
        main_layout.addWidget(self.availability_table)
        main_layout.addWidget(book_now_btn)
        main_layout.addStretch()

        # Load initial availability
        self.load_availability_and_times()

        # Apply styles
        self.setStyleSheet("""
            #facility-header {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid #e0e0e0;
            }
            #back-button {
                background-color: transparent;
                color: #3498db;
                border: none;
                padding: 5px 0;
                text-align: left;
                font-weight: bold;
            }
            #facility-name {
                margin-top: 10px;
                color: #2c3e50;
            }
            #facility-info {
                color: #7f8c8d;
                font-size: 14px;
            }
            #facility-description {
                color: #34495e;
                font-size: 14px;
                margin-top: 5px;
            }
            #facility-location {
                color: #555;
                font-size: 13px;
                font-style: italic;
            }
            #section-header {
                color: #2c3e50;
                border-bottom: 1px solid #ecf0f1;
                padding-bottom: 5px;
                margin-top: 20px;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                selection-background-color: #a7d9ff; /* Lighter blue for selection */
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
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
                padding: 10px 15px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton#action-button:hover {
                background-color: #2980b9;
            }
            QDateEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: #2c3e50;
                min-height: 25px;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: 1px solid #ddd;
            }
            QDateEdit::down-arrow {
                image: url(ui/icons/calendar.png); /* Replace with your actual calendar icon path */
                width: 16px;
                height: 16px;
            }
        """)

    def load_availability_and_times(self):
        """Loads and displays availability for the selected date."""
        selected_date_str = self.booking_date_selector.date().toString("yyyy-MM-dd")
        booked_slots = get_facility_availability(self.facility_id, selected_date_str)

        self.availability_table.setRowCount(0)

        # Generate all possible 30-minute slots for the day (e.g., 8 AM to 10 PM)
        start_hour = 8
        end_hour = 22  # 10 PM
        all_slots = []
        current_time_dt = datetime.datetime.strptime(f"{selected_date_str} {start_hour}:00", "%Y-%m-%d %H:%M")
        while current_time_dt.hour < end_hour or (current_time_dt.hour == end_hour and current_time_dt.minute == 0):
            all_slots.append(current_time_dt)
            current_time_dt += datetime.timedelta(minutes=30)

        row_idx = 0
        for i in range(len(all_slots) - 1):
            slot_start = all_slots[i]
            slot_end = all_slots[i+1]

            is_booked = False
            for booked in booked_slots:
                if (booked['start_time'] < slot_end and booked['end_time'] > slot_start):
                    is_booked = True
                    break
            
            # Treat past slots on the current day as booked/unavailable
            if self.booking_date_selector.date() == QDate.currentDate() and slot_start < datetime.datetime.now():
                is_booked = True

            self.availability_table.insertRow(row_idx)
            start_item = QTableWidgetItem(slot_start.strftime("%H:%M"))
            end_item = QTableWidgetItem(slot_end.strftime("%H:%M"))

            if is_booked:
                start_item.setForeground(QColor("red"))
                end_item.setForeground(QColor("red"))
                status_text = "Booked"
            else:
                start_item.setForeground(QColor("green"))
                end_item.setForeground(QColor("green"))
                status_text = "Available"

            self.availability_table.setItem(row_idx, 0, start_item)
            self.availability_table.setItem(row_idx, 1, end_item)
            # You can add a third column for status if desired
            # self.availability_table.setItem(row_idx, 2, QTableWidgetItem(status_text))
            row_idx += 1
        
        if row_idx == 0:
            self.availability_table.setRowCount(1)
            no_slots_item = QTableWidgetItem("No time slots available for this date.")
            no_slots_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.availability_table.setSpan(0, 0, 1, 2)
            self.availability_table.setItem(0, 0, no_slots_item)


    def open_booking_dialog(self):
        """Opens the BookingDialog for the current facility and selected date."""
        dialog = BookingDialog(
            self,
            user_id=self.user_id, # Pass the user ID
            facility=self.facility_data,
            selected_date=self.booking_date_selector.date().toPython()
        )
        if dialog.exec():
            # If booking is successful, refresh availability
            self.load_availability_and_times()
            # Optionally, emit a signal to the parent dashboard to refresh 'My Bookings'
            # (e.g., self.parent().load_all_my_bookings() if you have a direct parent reference)

    # --- Helper Message Box Functions (copied from StudentDashboard for consistency) ---
    def show_styled_message_box(self, icon, title, text, buttons=QMessageBox.StandardButton.Ok):
        """Show a styled message box that matches the app theme"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)

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
    