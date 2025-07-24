# Smart Campus Navigation and Facility Booking System

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)

A comprehensive system designed to enhance campus experience by providing smart navigation and efficient facility booking for students, faculty, and administrators. This platform streamlines the process of finding locations and reserving campus resources.

## Key Features

### For Students
- User registration and login
- **Find and browse campus facilities** (e.g., study rooms, labs, lecture halls, sports venues) by type, building, capacity, and availability.
- **View detailed facility information** and real-time availability.
- **Book facilities for specific time slots and purposes**.
- **View and manage their upcoming, past, and cancelled bookings**.
- **Access a campus map** for navigation (placeholder feature).
- Update personal profile details.

### For Faculty/Staff
- User registration and login
- **Find and browse campus facilities** by type, building, capacity, and availability.
- **View detailed facility information** and real-time availability.
- **Book facilities for specific time slots and purposes**.
- **View and manage their upcoming, past, and cancelled bookings**.
- **View personal usage reports** (e.g., total bookings, hours booked, most used facilities).
- Update personal profile details.

### For Administrators
- System-wide management dashboard
- User account management (students, faculty, other admins), including activation/suspension.
- **Building management** (add, edit, delete buildings).
- **Facility management** (add, edit, delete facilities, manage bookable status and eligibility).
- **Booking management** (view, search, and update status of all bookings).
- System metrics and analytics on facility utilization and booking trends.
- **Booking rule configuration** (e.g., max duration, min advance notice, concurrent bookings per user per facility type).
- Database backup and maintenance tools.

## System Requirements

### Windows/macOS
- Windows 10 or later / macOS 10.14 (Mojave) or later
- Python 3.8 to 3.11 (3.12+ haven't been tested yet)
- MySQL Server 8.0 or later
- 4GB RAM minimum
- 500MB free disk space

## Installation Guide

### 1. Install Python

#### Windows
1. Download Python 3.9 or 3.10 from the [official website](https://www.python.org/downloads/)
2. Run the installer
3. **Important**: Check the box that says "Add Python to PATH" during installation
4. Complete the installation

#### macOS
1. Install Homebrew if you don't have it:
    ```bash
    /bin/bash -c "$(curl -fsSL [https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh](https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh))"
    ```
2. Install Python using Homebrew:
    ```bash
    brew install python@3.9
    ```

### 2. Install MySQL

#### Windows
1. Download MySQL Server from the [official website](https://dev.mysql.com/downloads/mysql/)
2. Run the installer
3. Choose "Developer Default" installation type
4. Follow the installation wizard
5. **Important**: Remember the root password you set during installation

#### macOS
1. Install MySQL using Homebrew:
    ```bash
    brew install mysql
    ```
2. Start MySQL service:
    ```bash
    brew services start mysql
    ```
3. Set root password:
    ```bash
    mysql_secure_installation
    ```

### 3. Clone the Repository

1. Download and install [Git](https://git-scm.com/downloads) if you don't have it
2. Open Command Prompt (Windows) or Terminal (macOS)
3. Navigate to your desired directory
4. Run the following command:
    ```bash
    git clone [https://github.com/your_repo_name/Smart-Campus-Navigation-and-Facility-Booking-System.git](https://github.com/your_repo_name/Smart-Campus-Navigation-and-Facility-Booking-System.git) # Updated repo name
    ```
5. Navigate to the project directory:
    ```bash
    cd Smart-Campus-Navigation-and-Facility-Booking-System # Updated directory name
    ```

### 4. Configure Environment Variables

1. Create a new file named `.env` in the project root directory
2. Add the following content:

DB_HOST=localhost
DB_USER=your_mysql_user # Recommended: change from 'root' to a dedicated user
DB_PASSWORD=your_mysql_password
DB_NAME=smart_campus_db # Updated database name


### 5. Set Up a Virtual Environment and Install Required Packages

1. Create and activate a virtual environment:

#### Windows
```bash
python -m venv .venv
.\.venv\Scripts\activate
macOS
Bash

python3 -m venv .venv
source .venv/bin/activate
Install the required packages:
Bash

pip install -r requirements.txt
6. Set Up the Database
In the project directory, run:
Bash

python setup_database.py
This will create the database and all necessary tables automatically. Ensure your setup_database.py script is updated for the SCNFBS schema.
7. Launch the Application In the project directory, run:
Bash

python main.py
The application will start with the login screen.
Technical Notes
The application uses PySide6 for the UI components.
Charts and visualizations in the admin dashboard are rendered using matplotlib (if applicable).
MySQL is used for database storage.
All database interactions are handled through the db_utils.py module.
(Optional) Real-time updates: The system can be extended to use MQTT for real-time notifications (e.g., booking status changes), though this is not part of the core initial implementation.
User Guide
Student Interface
Register a new account or login with existing credentials.
Browse or search for available facilities by building, type, capacity, or date.
View detailed information about a facility and its time slot availability.
Book a facility for a specific purpose and time.
View and manage your upcoming, past, and cancelled bookings.
Explore campus navigation features.
Update your profile information.
Faculty/Staff Interface
Login with faculty/staff credentials.
Browse or search for available facilities, similar to students.
Book facilities for academic or official purposes.
Manage their own bookings and view usage reports for their account.
Update their profile information.
Admin Interface
Login with admin credentials.
Manage user accounts (students, faculty).
Add, edit, or delete buildings and facilities.
Oversee all bookings, including approval (if 'Pending Approval' status is used), cancellation, and completion.
View system-wide metrics and reports on facility utilization.
Configure booking rules for different facility types.
Perform database backup and maintenance tasks.
Troubleshooting
Common Issues
Database Connection Error:
Windows: Verify your MySQL server is running (check Services).
macOS: Run brew services list to check MySQL status.
Check your .env file has correct credentials.
Make sure MySQL is running on the default port (3306).
Ensure the database name in .env (smart_campus_db) matches the one you created in MySQL.
Login Problems:
Reset your password or contact an administrator.
Default admin credentials (for initial setup):
Username: admin
Password: admin123
Ensure the user account is active.
Application Won't Start:
Make sure Python is in your PATH.
Verify the database setup script (setup_database.py) has been run with the new schema.
Check the console for error messages.
On macOS, if you see font warnings, they can be safely ignored.
Platform-Specific Issues
Windows
If you get a "MySQL service not found" error:
Open Services (services.msc)
Look for "MySQL80" or similar
Start the service if it's not running
macOS
If you get authentication errors:
Check if MySQL is running: brew services list
Try restarting MySQL: brew services restart mysql
Verify root password: mysql -u root -p
Getting Help
If you encounter any issues not covered here, please:

Check the console output for error messages.
Verify all installation steps were completed.
Contact us through a pull request (or your designated support channel)
