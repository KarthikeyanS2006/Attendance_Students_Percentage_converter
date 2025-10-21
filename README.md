# Student Attendance Percentage Calculator

A Python-based desktop application for calculating student attendance percentages with year/department group selection and automated email notifications for low attendance students.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- ✅ **Attendance Percentage Calculation**: Automatically calculate attendance percentage for individual students
- 📊 **Year & Department Selection**: Filter and manage students by year and department groups
- ⚠️ **Low Attendance Alerts**: Identify students below attendance threshold (e.g., 75%)
- 📧 **Email Notifications**: Send automated email alerts to students with low attendance
- 🖥️ **GUI Interface**: User-friendly Tkinter-based graphical interface
- 💾 **Data Management**: Store and retrieve attendance records from Excel/CSV files
- 📈 **Report Generation**: Generate attendance reports for analysis

## Prerequisites

- Python 3.7 or higher installed on your system
- Basic knowledge of running Python scripts

## Installation

### Step 1: Clone the Repository


git clone https://github.com/yourusername/Attendance_Students_Percentage_converter.git




### Step 2: Install Required Libraries

pip install pandas openpyxl tkinter smtplib


Or install from requirements file:

pip install -r requirements.txt



### Step 3: Prepare Student Data File

Create an Excel file named `students.xlsx` with these columns:

| Roll Number | Name | Department | Year | Email | Total Days | Present Days |
|-------------|------|------------|------|-------|------------|--------------|
| 101 | John Doe | CSE | 3 | john@email.com | 100 | 85 |
| 102 | Jane Smith | ECE | 2 | jane@email.com | 100 | 70 |

### Step 4: Configure Email Settings

Edit the email configuration in `email_sender.py`:

Email Configuration
SENDER_EMAIL = "your-email@gmail.com"
APP_PASSWORD = "your-16-digit-app-password"
SMTP_SERVER = "smtp.gmail.com"



**Important**: For Gmail, generate an App Password from:  
Google Account Settings → Security → 2-Step Verification → App Passwords

## Usage

### Running the Main Program

python attendance_calculator.py



The GUI window will open automatically.

### Calculate Attendance Percentage

1. **Select Department**: Choose department from dropdown (CSE, ECE, MECH, etc.)
2. **Select Year**: Choose year group (1st Year, 2nd Year, 3rd Year)
3. **Load Students**: Click "Load Students" button to display filtered students
4. **View Percentages**: The system automatically calculates and displays attendance percentage

**Formula used**: `Attendance % = (Present Days / Total Days) × 100`

### Mark Daily Attendance

1. Select the date using the date picker
2. Select department and year group
3. Mark each student as Present (P) or Absent (A)
4. Click "Save Attendance" to update records

### Send Email Notifications

1. Click on "Low Attendance Alerts" button
2. Set threshold percentage (default: 75%)
3. System identifies students below threshold
4. Review the list of students with low attendance
5. Click "Send Email Notifications" to alert students

**Email template includes**:
- Student name and roll number
- Current attendance percentage
- Number of absent days
- Reminder to improve attendance

### View Reports

1. Go to "Reports" tab
2. Select date range or department filter
3. Click "Generate Report"
4. Export to Excel or PDF format

## Application Interface

### Main Dashboard

- **Student List**: Shows all students with roll number, name, and percentage
- **Filter Controls**: Department and Year dropdown menus
- **Status Indicator**: Color-coded percentage display
  - 🟢 Green: ≥75%
  - 🟡 Yellow: 65-74%
  - 🔴 Red: <65%

### Buttons and Functions

- **Load Students**: Refresh student list based on filters
- **Calculate All**: Recalculate all attendance percentages
- **Send Alerts**: Trigger email notifications for low attendance
- **Export Data**: Save data to Excel file

## Configuration

Edit these settings in the code:
Attendance Settings
MINIMUM_ATTENDANCE = 75 # Threshold percentage
TOTAL_WORKING_DAYS = 100 # Total class days per semester
WARNING_THRESHOLD = 70 # Yellow warning level

Departments
DEPARTMENTS = ["CSE", "ECE", "MECH", "CIVIL", "EEE"]

Years
YEARS = ["1", "2", "3", "4"]



## Troubleshooting

### Email Not Sending

- Check email credentials are correct
- Use App Password, not regular Gmail password
- Verify internet connection
- Check spam folder if emails not received

### Excel File Not Loading

- Ensure `students.xlsx` is in the same folder as the Python script
- Check file is not open in Excel while running program
- Verify column names match exactly

### GUI Not Opening

- Install tkinter: `pip install tk`
- For Linux: `sudo apt-get install python3-tk`
- Restart computer after installation

### Percentage Not Calculating

- Ensure "Total Days" and "Present Days" columns have numeric values
- Check for blank or zero values
- Reload the Excel file

## File Structure

attendance-calculator/
│
├── attendance_calculator.py # Main application (GUI)
├── email_sender.py # Email notification module
├── students.xlsx # Student database
├── attendance_records.xlsx # Daily attendance records
├── requirements.txt # Python dependencies
└── README.md # This documentation



## Security Best Practices

- ⚠️ Never share your email App Password
- 🔒 Keep student data files secure
- 💾 Backup Excel files regularly
- 🔑 Use environment variables for sensitive data

## Future Enhancements

- [ ] SMS notifications using Twilio API
- [ ] Parent email notifications
- [ ] Biometric attendance integration
- [ ] Cloud database sync with Firebase
- [ ] Mobile app version using Flutter

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or issues, please open an issue on GitHub or contact the maintainer.

## Credits

Developed for educational purposes at Sethupathy Government Arts College, Manamadurai.

**Developer**: Karthikeyan  
**Institution**: Sethupathy Government Arts College  
**Location**: Manamadurai, Tamil Nadu, India

## Quick Start Commands

Install dependencies
pip install pandas openpyxl tkinter

Run the application
python attendance_calculator.py

Calculate attendance for specific department
python attendance_calculator.py --department CSE --year 3



## Screenshots

_Add screenshots of your application here_

## Acknowledgments

- Thanks to all contributors
- Inspired by the need for efficient attendance management systems
- Built with Python and Tkinter

---

**⭐ If you find this project useful, please consider giving it a star!**
requirements.txt File
Create this file with the following content:


pandas>=1.3.0
openpyxl>=3.0.0
Additional GitHub Repository Setup Tips
Repository Topics/Tags
Add these topics to your GitHub repository for better discoverability :​


python
attendance-system
education
tkinter
email-notifications
student-management
gui-application
excel
pandas
college-management
.gitignore File
Create a .gitignore file to exclude sensitive data :​


# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/

# Data files
students.xlsx
attendance_records.xlsx
*.csv

# Config files with sensitive data
config.py
.env

# IDE
.vscode/
.idea/
*.swp
*.swo
Short Descriptions for Different Uses
50 characters (for GitHub description field) :​


Python attendance tracker with email alerts
100 characters (extended version) :​


Python desktop app for student attendance tracking with percentage calculation and email notifications
