import os
import sys
import csv
import sqlite3
import shutil
import smtplib
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import time

class AttendanceSystem:
    def __init__(self):
        # Create directory structure
        self.data_dir = "attendance_records"
        self.reports_dir = os.path.join(self.data_dir, "attendance_reports_pdf")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        self.db_file = os.path.join(self.data_dir, "attendance.db")
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self.init_database()
    
    def get_connection(self):
        """Get database connection with proper timeout and WAL mode - FIXES DATABASE LOCK"""
        conn = sqlite3.connect(self.db_file, timeout=30.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for concurrency
        conn.execute('PRAGMA busy_timeout=30000')  # 30 second timeout
        return conn
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                year TEXT NOT NULL,
                department TEXT NOT NULL,
                total_classes INTEGER DEFAULT 0,
                present_classes INTEGER DEFAULT 0,
                absent_classes INTEGER DEFAULT 0,
                percentage REAL DEFAULT 0.0,
                status TEXT,
                created_date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY,
                sender_email TEXT,
                sender_password TEXT,
                hod_email TEXT,
                threshold_percentage REAL DEFAULT 75.0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_percentage(self, total, present):
        if total > 0:
            return round((present / total) * 100, 2)
        return 0.0
    
    def get_status(self, percentage):
        """Get attendance status: <60% = Critical, 60-74% = Warning, 75%+ = Good"""
        if percentage >= 75:
            return "Good"
        elif percentage >= 60:
            return "Warning"
        else:
            return "Critical"
    
    def add_student(self, student_id, name, email, year, department, total, present, absent):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                percentage = self.calculate_percentage(total, present)
                status = self.get_status(percentage)
                created_date = datetime.now().strftime('%Y-%m-%d')
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ''', (student_id, name, email, year, department, total, present, 
                      absent, percentage, status, created_date))
                
                conn.commit()
                conn.close()
                return True, f"Student {name} added successfully!"
            except sqlite3.IntegrityError:
                return False, "Student ID already exists!"
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return False, str(e)
            except Exception as e:
                return False, str(e)
    
    def update_student(self, student_id, name, email, year, department, total, present, absent):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                percentage = self.calculate_percentage(total, present)
                status = self.get_status(percentage)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE students SET name=?, email=?, year=?, department=?, 
                    total_classes=?, present_classes=?, absent_classes=?, percentage=?, status=?
                    WHERE student_id=?
                ''', (name, email, year, department, total, present, absent, percentage, status, student_id))
                conn.commit()
                conn.close()
                return True, "Student updated successfully!"
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return False, str(e)
            except Exception as e:
                return False, str(e)
    
    def delete_student(self, student_id):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM students WHERE student_id=?", (student_id,))
                conn.commit()
                conn.close()
                return True, "Student deleted successfully!"
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return False, str(e)
            except Exception as e:
                return False, str(e)
    
    def get_all_students(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students ORDER BY name")
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                conn.close()
                return [dict(zip(columns, row)) for row in rows]
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return []
            except:
                return []
    
    def get_students_by_year_dept(self, year, department):
        """Get students filtered by year and department for bulk email"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                if year == "All" and department == "All":
                    cursor.execute("SELECT * FROM students ORDER BY name")
                elif year == "All":
                    cursor.execute("SELECT * FROM students WHERE department=? ORDER BY name", (department,))
                elif department == "All":
                    cursor.execute("SELECT * FROM students WHERE year=? ORDER BY name", (year,))
                else:
                    cursor.execute("SELECT * FROM students WHERE year=? AND department=? ORDER BY name", 
                                 (year, department))
                
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                conn.close()
                return [dict(zip(columns, row)) for row in rows]
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return []
            except:
                return []
    
    def search_student(self, student_id):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students WHERE student_id=?", (student_id,))
                columns = [d[0] for d in cursor.description]
                row = cursor.fetchone()
                conn.close()
                return dict(zip(columns, row)) if row else None
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            except:
                return None
    
    def search_by_name(self, name):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students WHERE name LIKE ?", (f'%{name}%',))
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                conn.close()
                return [dict(zip(columns, row)) for row in rows]
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return []
            except:
                return []
    
    def filter_by_status(self, status):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                if status == "All":
                    cursor.execute("SELECT * FROM students ORDER BY percentage DESC")
                else:
                    cursor.execute("SELECT * FROM students WHERE status=? ORDER BY percentage DESC", (status,))
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                conn.close()
                return [dict(zip(columns, row)) for row in rows]
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return []
            except:
                return []
    
    def get_statistics(self):
        """Get comprehensive statistics with year and department breakdown"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM students")
                total = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(percentage) FROM students")
                avg = cursor.fetchone()[0]
                
                cursor.execute("SELECT status, COUNT(*) FROM students GROUP BY status")
                status_dist = dict(cursor.fetchall())
                
                cursor.execute("SELECT year, COUNT(*) FROM students GROUP BY year")
                year_dist = dict(cursor.fetchall())
                
                cursor.execute("SELECT department, COUNT(*), AVG(percentage) FROM students GROUP BY department")
                dept_stats = cursor.fetchall()
                
                cursor.execute("SELECT COUNT(*) FROM students WHERE percentage < 60")
                critical_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM students WHERE percentage >= 60 AND percentage < 75")
                warning_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM students WHERE percentage >= 75")
                good_count = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_students': total,
                    'average_percentage': round(avg, 2) if avg else 0,
                    'status_distribution': status_dist,
                    'year_distribution': year_dist,
                    'department_stats': dept_stats,
                    'critical_count': critical_count,
                    'warning_count': warning_count,
                    'good_count': good_count
                }
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            except:
                return None
    
    def create_backup(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f"attendance_backup_{timestamp}.db")
            shutil.copy2(self.db_file, backup_file)
            return True, f"Backup created: attendance_backup_{timestamp}.db"
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
    
    def generate_pdf_report(self, student_id):
        student = self.search_student(student_id)
        if not student:
            return False, "Student not found!", None
        
        try:
            filename = f"Attendance_{student_id}_{student['name'].replace(' ', '_')}.pdf"
            filepath = os.path.join(self.reports_dir, filename)
            
            c = canvas.Canvas(filepath, pagesize=A4)
            width, height = A4
            
            # Red header
            c.setFillColor(colors.HexColor('#CC0000'))
            c.rect(0, height - 120, width, 120, fill=True, stroke=False)
            
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(width/2, height - 50, "SETHUPATHY GOVERNMENT ARTS COLLEGE")
            
            c.setFont("Helvetica", 14)
            c.drawCentredString(width/2, height - 75, "RAMANATHAPURAM")
            
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, height - 100, "STUDENT ATTENDANCE REPORT")
            
            # Student details
            c.setFillColor(colors.black)
            y = height - 160
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"Student ID: {student['student_id']}")
            c.drawString(350, y, f"Date: {datetime.now().strftime('%d-%m-%Y')}")
            
            y -= 25
            c.drawString(50, y, f"Name: {student['name']}")
            y -= 25
            c.drawString(50, y, f"Year: {student['year']}")
            y -= 25
            c.drawString(50, y, f"Department: {student['department']}")
            
            # Line separator
            y -= 20
            c.setStrokeColor(colors.HexColor('#CC0000'))
            c.setLineWidth(2)
            c.line(50, y, width - 50, y)
            
            # Table header
            y -= 40
            c.setFillColor(colors.HexColor('#CC0000'))
            c.rect(50, y - 5, width - 100, 30, fill=True, stroke=False)
            
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(70, y + 5, "Attendance Details")
            
            # Data
            y -= 30
            c.setFont("Helvetica", 11)
            
            data = [
                ("Total Classes:", str(student['total_classes'])),
                ("Present:", str(student['present_classes'])),
                ("Absent:", str(student['absent_classes'])),
                ("Percentage:", f"{student['percentage']}%"),
                ("Status:", student['status'])
            ]
            
            for i, (label, value) in enumerate(data):
                if i % 2 == 0:
                    c.setFillColor(colors.HexColor('#F0F0F0'))
                    c.rect(50, y - 5, width - 100, 25, fill=True, stroke=False)
                
                c.setFillColor(colors.black)
                c.drawString(70, y + 5, label)
                c.drawString(350, y + 5, value)
                y -= 25
            
            # Status indicator with color coding
            y -= 20
            c.setLineWidth(2)
            c.line(50, y, width - 50, y)
            
            y -= 30
            c.setFont("Helvetica-Bold", 12)
            
            # Color based on status
            if student['status'] == 'Good':
                c.setFillColor(colors.HexColor('#28a745'))
            elif student['status'] == 'Warning':
                c.setFillColor(colors.HexColor('#ff8c00'))
            else:
                c.setFillColor(colors.HexColor('#dc3545'))
            
            c.drawString(70, y, f"Status: {student['status']}")
            
            # Requirements box
            y -= 50
            c.setFillColor(colors.HexColor('#F0F0F0'))
            c.rect(50, y - 60, width - 100, 70, fill=True, stroke=True)
            
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(70, y - 10, "ATTENDANCE REQUIREMENTS:")
            
            c.setFont("Helvetica", 10)
            c.drawString(70, y - 25, "• Good (Green): 75% and above")
            c.drawString(70, y - 40, "• Warning (Orange): 60% to 74%")
            c.drawString(70, y - 55, "• Critical (Red): Below 60%")
            
            # Footer
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.gray)
            c.drawCentredString(width/2, 50, "This is a computer-generated attendance report")
            
            c.save()
            return True, "PDF generated successfully!", filepath
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def save_email_settings(self, sender_email, sender_password, hod_email, threshold):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO email_settings 
                    VALUES (1, ?, ?, ?, ?)
                ''', (sender_email, sender_password, hod_email, threshold))
                conn.commit()
                conn.close()
                return True
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return False
            except:
                return False
    
    def get_email_settings(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM email_settings WHERE id=1")
                row = cursor.fetchone()
                conn.close()
                if row:
                    return {
                        'sender_email': row[1],
                        'sender_password': row[2],
                        'hod_email': row[3],
                        'threshold': row[4]
                    }
                return None
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            except:
                return None


class AttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Attendance Management System - Sethupathy Government Arts College")
        self.root.geometry("1100x750")
        self.root.configure(bg="#f0f0f0")
        
        self.system = AttendanceSystem()
        
        # ALL 12 Departments from Sethupathy Government Arts College
        self.departments = [
            "Department of Tamil",
            "Department of English",
            "Department of Mathematics",
            "Department of Physics",
            "Department of Chemistry",
            "Department of Economics",
            "Department of Commerce",
            "Department of Commerce (Computer Applications)",
            "Department of Botany",
            "Department of Zoology",
            "Department of Marine Biology",
            "Department of Computer Science"
        ]
        
        # Years
        self.years = ["1st Year", "2nd Year", "3rd Year"]
        
        self.sender_email = ""
        self.sender_password = ""
        self.hod_email = ""
        
        settings = self.system.get_email_settings()
        if settings:
            self.sender_email = settings['sender_email']
            self.sender_password = settings['sender_password']
            self.hod_email = settings['hod_email']
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_header()
        self.create_notebook()
    
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Exit application?"):
            try:
                self.root.quit()
                self.root.destroy()
                sys.exit(0)
            except:
                sys.exit(0)
    
    def exit_application(self):
        if messagebox.askokcancel("Exit", "Are you sure?"):
            try:
                self.root.quit()
                self.root.destroy()
                sys.exit(0)
            except:
                sys.exit(0)
    
    def create_header(self):
        header = tk.Frame(self.root, bg="#CC0000", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="SETHUPATHY GOVERNMENT ARTS COLLEGE",
                font=("Arial", 20, "bold"), bg="#CC0000", fg="white").pack(pady=10)
        tk.Label(header, text="RAMANATHAPURAM",
                font=("Arial", 12), bg="#CC0000", fg="white").pack()
        tk.Label(header, text="Attendance Management System",
                font=("Arial", 11, "italic"), bg="#CC0000", fg="white").pack(pady=5)
        
        exit_btn = tk.Button(header, text="✕ Exit", font=("Arial", 10, "bold"),
                            bg="white", fg="#CC0000", padx=15, pady=5,
                            command=self.exit_application, cursor="hand2")
        exit_btn.place(relx=0.95, rely=0.5, anchor="e")
    
    def create_notebook(self):
        style = ttk.Style()
        style.configure("TNotebook", background="#f0f0f0")
        style.configure("TFrame", background="#f0f0f0")
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.add_tab = ttk.Frame(notebook)
        notebook.add(self.add_tab, text="  Add Student  ")
        self.create_add_student_tab()
        
        self.view_tab = ttk.Frame(notebook)
        notebook.add(self.view_tab, text="  View All Students  ")
        self.create_view_students_tab()
        
        self.search_tab = ttk.Frame(notebook)
        notebook.add(self.search_tab, text="  Search & Filter  ")
        self.create_search_tab()
        
        self.report_tab = ttk.Frame(notebook)
        notebook.add(self.report_tab, text="  Generate Report  ")
        self.create_generate_report_tab()
        
        self.email_tab = ttk.Frame(notebook)
        notebook.add(self.email_tab, text="  Send Bulk Emails  ")
        self.create_email_tab()
        
        self.analytics_tab = ttk.Frame(notebook)
        notebook.add(self.analytics_tab, text="  Analytics  ")
        self.create_analytics_tab()
        
        self.settings_tab = ttk.Frame(notebook)
        notebook.add(self.settings_tab, text="  Settings  ")
        self.create_settings_tab()
    
    def create_add_student_tab(self):
        form_frame = tk.Frame(self.add_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(form_frame, text="Add New Student", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=15)
        
        fields_frame = tk.Frame(form_frame, bg="#ffffff")
        fields_frame.pack(padx=30, pady=10)
        
        # Fields
        tk.Label(fields_frame, text="Student ID:", font=("Arial", 11),
                bg="#ffffff").grid(row=0, column=0, sticky="w", pady=10)
        self.student_id_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.student_id_entry.grid(row=0, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Name:", font=("Arial", 11),
                bg="#ffffff").grid(row=1, column=0, sticky="w", pady=10)
        self.name_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.name_entry.grid(row=1, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Email:", font=("Arial", 11),
                bg="#ffffff").grid(row=2, column=0, sticky="w", pady=10)
        self.email_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.email_entry.grid(row=2, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Year:", font=("Arial", 11),
                bg="#ffffff").grid(row=3, column=0, sticky="w", pady=10)
        self.year_combo = ttk.Combobox(fields_frame, font=("Arial", 11), width=28,
                                      values=self.years, state="readonly")
        self.year_combo.grid(row=3, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Department:", font=("Arial", 11),
                bg="#ffffff").grid(row=4, column=0, sticky="w", pady=10)
        self.dept_combo = ttk.Combobox(fields_frame, font=("Arial", 11), width=28,
                                      values=self.departments, state="readonly")
        self.dept_combo.grid(row=4, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Total Classes:", font=("Arial", 11),
                bg="#ffffff").grid(row=5, column=0, sticky="w", pady=10)
        self.total_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.total_entry.grid(row=5, column=1, padx=20, pady=10)
        self.total_entry.bind('<KeyRelease>', self.calc_percentage)
        
        tk.Label(fields_frame, text="Present Classes:", font=("Arial", 11),
                bg="#ffffff").grid(row=6, column=0, sticky="w", pady=10)
        self.present_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.present_entry.grid(row=6, column=1, padx=20, pady=10)
        self.present_entry.bind('<KeyRelease>', self.calc_percentage)
        
        tk.Label(fields_frame, text="Absent Classes:", font=("Arial", 11),
                bg="#ffffff").grid(row=7, column=0, sticky="w", pady=10)
        self.absent_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.absent_entry.grid(row=7, column=1, padx=20, pady=10)
        
        tk.Label(fields_frame, text="Percentage:", font=("Arial", 11),
                bg="#ffffff").grid(row=8, column=0, sticky="w", pady=10)
        self.pct_label = tk.Label(fields_frame, text="0.00%", font=("Arial", 11, "bold"),
                                 bg="#ffffff", fg="blue")
        self.pct_label.grid(row=8, column=1, sticky="w", padx=20, pady=10)
        
        tk.Label(fields_frame, text="Status:", font=("Arial", 11),
                bg="#ffffff").grid(row=9, column=0, sticky="w", pady=10)
        self.status_label = tk.Label(fields_frame, text="N/A", font=("Arial", 11, "bold"),
                                     bg="#ffffff", fg="gray")
        self.status_label.grid(row=9, column=1, sticky="w", padx=20, pady=10)
        
        # Buttons
        button_frame = tk.Frame(form_frame, bg="#ffffff")
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Add Student", font=("Arial", 11, "bold"),
                 bg="#CC0000", fg="white", width=15, command=self.add_student_action,
                 cursor="hand2").pack(side="left", padx=10)
        tk.Button(button_frame, text="Clear Form", font=("Arial", 11),
                 bg="#666666", fg="white", width=15, command=self.clear_form,
                 cursor="hand2").pack(side="left", padx=10)
    
    def calc_percentage(self, event=None):
        try:
            total = int(self.total_entry.get())
            present = int(self.present_entry.get())
            if total > 0:
                pct = (present / total) * 100
                
                # Color coding: <60% = Critical (Red), 60-74% = Warning (Orange), 75%+ = Good (Green)
                if pct >= 75:
                    color = 'green'
                    status = 'Good'
                    status_color = 'green'
                elif pct >= 60:
                    color = 'orange'
                    status = 'Warning'
                    status_color = 'orange'
                else:
                    color = 'red'
                    status = 'Critical'
                    status_color = 'red'
                
                self.pct_label.config(text=f"{pct:.2f}%", fg=color)
                self.status_label.config(text=status, fg=status_color)
        except:
            self.pct_label.config(text="0.00%", fg="blue")
            self.status_label.config(text="N/A", fg="gray")
    
    def add_student_action(self):
        try:
            sid = self.student_id_entry.get().strip()
            name = self.name_entry.get().strip()
            email = self.email_entry.get().strip()
            year = self.year_combo.get()
            dept = self.dept_combo.get()
            total = int(self.total_entry.get())
            present = int(self.present_entry.get())
            absent = int(self.absent_entry.get())
            
            if not all([sid, name, year, dept]):
                messagebox.showerror("Error", "Please fill required fields (ID, Name, Year, Department)!")
                return
            
            if not email:
                if not messagebox.askyesno("No Email", "Email not provided. Continue without email?"):
                    return
            
            success, msg = self.system.add_student(sid, name, email, year, dept, total, present, absent)
            
            if success:
                messagebox.showinfo("Success", msg)
                self.clear_form()
                self.refresh_students()
                self.refresh_analytics()
            else:
                messagebox.showerror("Error", msg)
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers in Total/Present/Absent fields!")
    
    def clear_form(self):
        self.student_id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.year_combo.set('')
        self.dept_combo.set('')
        self.total_entry.delete(0, tk.END)
        self.present_entry.delete(0, tk.END)
        self.absent_entry.delete(0, tk.END)
        self.pct_label.config(text="0.00%", fg="blue")
        self.status_label.config(text="N/A", fg="gray")
    
    def create_view_students_tab(self):
        control_frame = tk.Frame(self.view_tab, bg="#f0f0f0")
        control_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(control_frame, text="🔄 Refresh", font=("Arial", 11, "bold"),
                 bg="#CC0000", fg="white", command=self.refresh_students,
                 cursor="hand2").pack(side="left", padx=5)
        tk.Button(control_frame, text="Export CSV", font=("Arial", 11, "bold"),
                 bg="#28a745", fg="white", command=self.export_csv,
                 cursor="hand2").pack(side="left", padx=5)
        
        tree_frame = tk.Frame(self.view_tab, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        self.tree = ttk.Treeview(tree_frame,
                                columns=("ID", "Name", "Email", "Year", "Dept", "Total", "Present", "Absent", "Pct", "Status"),
                                show="headings",
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        for col in ["ID", "Name", "Email", "Year", "Dept", "Total", "Present", "Absent", "Pct", "Status"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90 if col != "Dept" else 180)
        
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        
        # Tag colors for status
        self.tree.tag_configure('good', foreground='green')
        self.tree.tag_configure('warning', foreground='orange')
        self.tree.tag_configure('critical', foreground='red')
        
        # Delete button
        action_frame = tk.Frame(self.view_tab, bg="#f0f0f0")
        action_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(action_frame, text="Delete Selected", font=("Arial", 10, "bold"),
                 bg="#dc3545", fg="white", command=self.delete_student,
                 cursor="hand2").pack(side="left", padx=5)
        
        self.refresh_students()
    
    def refresh_students(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        students = self.system.get_all_students()
        for s in students:
            tag = 'good' if s['status'] == 'Good' else 'warning' if s['status'] == 'Warning' else 'critical'
            self.tree.insert("", "end", values=(
                s['student_id'], s['name'], s['email'] if s['email'] else 'N/A', 
                s['year'], s['department'],
                s['total_classes'], s['present_classes'], s['absent_classes'],
                f"{s['percentage']}%", s['status']
            ), tags=(tag,))
    
    def delete_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a student!")
            return
        
        if messagebox.askyesno("Confirm", "Delete this student?"):
            sid = self.tree.item(selected[0])['values'][0]
            self.system.delete_student(sid)
            self.refresh_students()
            self.refresh_analytics()
    
    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                               filetypes=[("CSV files", "*.csv")])
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Name', 'Email', 'Year', 'Department', 'Total', 'Present', 'Absent', 'Percentage', 'Status'])
                for s in self.system.get_all_students():
                    writer.writerow([s['student_id'], s['name'], s['email'], s['year'],
                                   s['department'], s['total_classes'], s['present_classes'],
                                   s['absent_classes'], s['percentage'], s['status']])
            messagebox.showinfo("Success", "Exported to CSV!")
    
    def create_search_tab(self):
        search_frame = tk.Frame(self.search_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        search_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(search_frame, text="Search & Filter", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=15)
        
        input_frame = tk.Frame(search_frame, bg="#ffffff")
        input_frame.pack(pady=20)
        
        tk.Label(input_frame, text="Search by Name:", font=("Arial", 11),
                bg="#ffffff").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.search_name_entry = tk.Entry(input_frame, font=("Arial", 11), width=30)
        self.search_name_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Button(input_frame, text="🔍 Search", font=("Arial", 10, "bold"),
                 bg="#CC0000", fg="white", command=self.search_by_name_action,
                 cursor="hand2").grid(row=0, column=2, padx=10)
        
        tk.Label(input_frame, text="Filter by Status:", font=("Arial", 11),
                bg="#ffffff").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.status_filter = ttk.Combobox(input_frame, values=["All", "Good", "Warning", "Critical"],
                                         font=("Arial", 11), width=28, state="readonly")
        self.status_filter.set("All")
        self.status_filter.grid(row=1, column=1, padx=10, pady=10)
        tk.Button(input_frame, text="Filter", font=("Arial", 10, "bold"),
                 bg="#CC0000", fg="white", command=self.filter_by_status_action,
                 cursor="hand2").grid(row=1, column=2, padx=10)
        
        results_frame = tk.Frame(search_frame, bg="#ffffff")
        results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        vsb = ttk.Scrollbar(results_frame, orient="vertical")
        
        self.search_tree = ttk.Treeview(results_frame,
                                        columns=("ID", "Name", "Email", "Year", "Dept", "Pct", "Status"),
                                        show="headings",
                                        yscrollcommand=vsb.set)
        
        vsb.config(command=self.search_tree.yview)
        
        for col in ["ID", "Name", "Email", "Year", "Dept", "Pct", "Status"]:
            self.search_tree.heading(col, text=col)
            width = 180 if col == "Dept" else 100 if col in ["Name", "Email"] else 80
            self.search_tree.column(col, width=width)
        
        self.search_tree.tag_configure('good', foreground='green')
        self.search_tree.tag_configure('warning', foreground='orange')
        self.search_tree.tag_configure('critical', foreground='red')
        
        vsb.pack(side="right", fill="y")
        self.search_tree.pack(fill="both", expand=True)
    
    def search_by_name_action(self):
        name = self.search_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a name!")
            return
        
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        students = self.system.search_by_name(name)
        if not students:
            messagebox.showinfo("No Results", f"No students found with '{name}'")
            return
        
        for s in students:
            tag = 'good' if s['status'] == 'Good' else 'warning' if s['status'] == 'Warning' else 'critical'
            self.search_tree.insert("", "end", values=(
                s['student_id'], s['name'], s['email'] if s['email'] else 'N/A',
                s['year'], s['department'],
                f"{s['percentage']}%", s['status']
            ), tags=(tag,))
    
    def filter_by_status_action(self):
        status = self.status_filter.get()
        
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        students = self.system.filter_by_status(status)
        for s in students:
            tag = 'good' if s['status'] == 'Good' else 'warning' if s['status'] == 'Warning' else 'critical'
            self.search_tree.insert("", "end", values=(
                s['student_id'], s['name'], s['email'] if s['email'] else 'N/A',
                s['year'], s['department'],
                f"{s['percentage']}%", s['status']
            ), tags=(tag,))
    
    def create_generate_report_tab(self):
        report_frame = tk.Frame(self.report_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        report_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(report_frame, text="Generate PDF Report", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=20)
        
        input_frame = tk.Frame(report_frame, bg="#ffffff")
        input_frame.pack(pady=20)
        
        tk.Label(input_frame, text="Student ID:", font=("Arial", 12),
                bg="#ffffff").pack(side="left", padx=10)
        self.report_id_entry = tk.Entry(input_frame, font=("Arial", 12), width=20)
        self.report_id_entry.pack(side="left", padx=10)
        tk.Button(input_frame, text="📄 Generate PDF", font=("Arial", 11, "bold"),
                 bg="#CC0000", fg="white", width=15,
                 command=self.generate_report_action, cursor="hand2").pack(side="left", padx=10)
        
        self.info_text = scrolledtext.ScrolledText(report_frame, width=90, height=22,
                                                   font=("Courier", 10), bg="#f9f9f9")
        self.info_text.pack(padx=20, pady=20)
    
    def generate_report_action(self):
        sid = self.report_id_entry.get().strip()
        if not sid:
            messagebox.showerror("Error", "Enter Student ID!")
            return
        
        student = self.system.search_student(sid)
        if not student:
            messagebox.showerror("Error", f"Student {sid} not found!")
            return
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, f"{'='*70}\n")
        self.info_text.insert(tk.END, f"SETHUPATHY GOVERNMENT ARTS COLLEGE - STUDENT ATTENDANCE REPORT\n")
        self.info_text.insert(tk.END, f"{'='*70}\n\n")
        self.info_text.insert(tk.END, f"Student ID    : {student['student_id']}\n")
        self.info_text.insert(tk.END, f"Name          : {student['name']}\n")
        self.info_text.insert(tk.END, f"Email         : {student['email'] if student['email'] else 'N/A'}\n")
        self.info_text.insert(tk.END, f"Year          : {student['year']}\n")
        self.info_text.insert(tk.END, f"Department    : {student['department']}\n\n")
        self.info_text.insert(tk.END, f"{'-'*70}\n")
        self.info_text.insert(tk.END, f"ATTENDANCE DETAILS:\n")
        self.info_text.insert(tk.END, f"{'-'*70}\n")
        self.info_text.insert(tk.END, f"Total Classes      : {student['total_classes']}\n")
        self.info_text.insert(tk.END, f"Classes Attended   : {student['present_classes']}\n")
        self.info_text.insert(tk.END, f"Classes Absent     : {student['absent_classes']}\n")
        self.info_text.insert(tk.END, f"Percentage         : {student['percentage']}%\n")
        self.info_text.insert(tk.END, f"Status             : {student['status']}\n")
        self.info_text.insert(tk.END, f"{'-'*70}\n\n")
        
        # Status explanation
        self.info_text.insert(tk.END, "STATUS LEGEND:\n")
        self.info_text.insert(tk.END, "✓ Good (Green)     : 75% and above\n")
        self.info_text.insert(tk.END, "⚠ Warning (Orange) : 60% to 74%\n")
        self.info_text.insert(tk.END, "✗ Critical (Red)   : Below 60%\n")
        self.info_text.insert(tk.END, f"{'-'*70}\n")
        
        success, msg, filepath = self.system.generate_pdf_report(sid)
        if success:
            self.info_text.insert(tk.END, f"\n✓ PDF Generated Successfully!\n")
            self.info_text.insert(tk.END, f"Location: {filepath}\n")
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
    
    def create_email_tab(self):
        """BULK EMAIL TAB - Send emails to all students by Year and Department"""
        email_frame = tk.Frame(self.email_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        email_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(email_frame, text="Send Bulk Email Notifications", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=15)
        
        # Filter section
        filter_frame = tk.LabelFrame(email_frame, text="Select Recipients",
                                     font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=15)
        filter_frame.pack(padx=20, pady=10, fill="x")
        
        tk.Label(filter_frame, text="Select Year:", font=("Arial", 11),
                bg="#ffffff").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.email_year_combo = ttk.Combobox(filter_frame, font=("Arial", 11), width=30,
                                            values=["All"] + self.years, state="readonly")
        self.email_year_combo.set("All")
        self.email_year_combo.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(filter_frame, text="Select Department:", font=("Arial", 11),
                bg="#ffffff").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.email_dept_combo = ttk.Combobox(filter_frame, font=("Arial", 11), width=30,
                                            values=["All"] + self.departments, state="readonly")
        self.email_dept_combo.set("All")
        self.email_dept_combo.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(filter_frame, text="Status Filter:", font=("Arial", 11),
                bg="#ffffff").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        self.email_status_combo = ttk.Combobox(filter_frame, font=("Arial", 11), width=30,
                                              values=["All", "Good", "Warning", "Critical"], state="readonly")
        self.email_status_combo.set("All")
        self.email_status_combo.grid(row=2, column=1, padx=10, pady=10)
        
        button_frame = tk.Frame(filter_frame, bg="#ffffff")
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        tk.Button(button_frame, text="Preview Recipients", font=("Arial", 10, "bold"),
                 bg="#007bff", fg="white", width=18, command=self.preview_recipients,
                 cursor="hand2").pack(side="left", padx=10)
        
        tk.Button(button_frame, text="📧 Send Emails", font=("Arial", 10, "bold"),
                 bg="#CC0000", fg="white", width=18, command=self.send_bulk_emails,
                 cursor="hand2").pack(side="left", padx=10)
        
        # Preview section
        preview_frame = tk.LabelFrame(email_frame, text="Recipients Preview",
                                      font=("Arial", 11, "bold"), bg="#ffffff")
        preview_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        tree_frame = tk.Frame(preview_frame, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        
        self.email_tree = ttk.Treeview(tree_frame,
                                       columns=("ID", "Name", "Email", "Year", "Dept", "Pct", "Status"),
                                       show="headings",
                                       yscrollcommand=vsb.set)
        
        vsb.config(command=self.email_tree.yview)
        
        for col in ["ID", "Name", "Email", "Year", "Dept", "Pct", "Status"]:
            self.email_tree.heading(col, text=col)
            width = 180 if col == "Dept" else 100
            self.email_tree.column(col, width=width)
        
        self.email_tree.tag_configure('good', foreground='green')
        self.email_tree.tag_configure('warning', foreground='orange')
        self.email_tree.tag_configure('critical', foreground='red')
        
        vsb.pack(side="right", fill="y")
        self.email_tree.pack(fill="both", expand=True)
        
        # Status label
        self.email_status_label = tk.Label(preview_frame, text="No recipients selected",
                                          font=("Arial", 10), bg="#ffffff", fg="gray")
        self.email_status_label.pack(pady=5)
        
        # Log section
        log_frame = tk.LabelFrame(email_frame, text="Email Log",
                                  font=("Arial", 11, "bold"), bg="#ffffff")
        log_frame.pack(padx=20, pady=10, fill="x")
        
        self.email_log = scrolledtext.ScrolledText(log_frame, width=90, height=8,
                                                   font=("Courier", 9), bg="#f9f9f9")
        self.email_log.pack(padx=10, pady=10)
    
    def preview_recipients(self):
        """Preview students who will receive emails"""
        year = self.email_year_combo.get()
        dept = self.email_dept_combo.get()
        status_filter = self.email_status_combo.get()
        
        # Clear tree
        for item in self.email_tree.get_children():
            self.email_tree.delete(item)
        
        # Get filtered students
        students = self.system.get_students_by_year_dept(year, dept)
        
        # Apply status filter
        if status_filter != "All":
            students = [s for s in students if s['status'] == status_filter]
        
        # Only students with email
        students_with_email = [s for s in students if s['email'] and s['email'].strip()]
        
        if not students_with_email:
            self.email_status_label.config(text="No students found with email addresses", fg="red")
            messagebox.showinfo("No Recipients", "No students found matching the criteria with email addresses.")
            return
        
        # Display in tree
        for s in students_with_email:
            tag = 'good' if s['status'] == 'Good' else 'warning' if s['status'] == 'Warning' else 'critical'
            self.email_tree.insert("", "end", values=(
                s['student_id'], s['name'], s['email'],
                s['year'], s['department'],
                f"{s['percentage']}%", s['status']
            ), tags=(tag,))
        
        self.email_status_label.config(text=f"Total Recipients: {len(students_with_email)} students",
                                      fg="green")
    
    def send_bulk_emails(self):
        """Send attendance warning emails to selected students"""
        if not self.sender_email or not self.sender_password:
            messagebox.showerror("Error", "Configure email settings first in the Settings tab!")
            return
        
        year = self.email_year_combo.get()
        dept = self.email_dept_combo.get()
        status_filter = self.email_status_combo.get()
        
        # Get students
        students = self.system.get_students_by_year_dept(year, dept)
        
        if status_filter != "All":
            students = [s for s in students if s['status'] == status_filter]
        
        students_with_email = [s for s in students if s['email'] and s['email'].strip()]
        
        if not students_with_email:
            messagebox.showerror("Error", "No students with email addresses found!")
            return
        
        # Confirm
        msg = f"Send emails to {len(students_with_email)} students?\n\n"
        msg += f"Year: {year}\n"
        msg += f"Department: {dept}\n"
        msg += f"Status: {status_filter}"
        
        if not messagebox.askyesno("Confirm", msg):
            return
        
        # Send emails
        success_count = 0
        fail_count = 0
        
        self.email_log.insert(tk.END, f"\n{'='*80}\n")
        self.email_log.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting bulk email...\n")
        self.email_log.insert(tk.END, f"Total recipients: {len(students_with_email)}\n")
        self.email_log.insert(tk.END, f"{'='*80}\n\n")
        
        for student in students_with_email:
            try:
                # Generate PDF
                success, msg_text, filepath = self.system.generate_pdf_report(student['student_id'])
                
                if not success:
                    self.email_log.insert(tk.END, f"[FAIL] {student['name']}: PDF generation failed\n")
                    fail_count += 1
                    continue
                
                # Prepare email
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = student['email']
                msg['Subject'] = f"Attendance Report - {student['name']}"
                
                # Email body based on status
                if student['status'] == 'Critical':
                    body = f"""Dear {student['name']},

This is an URGENT notice regarding your attendance.

Your Details:
- Student ID: {student['student_id']}
- Year: {student['year']}
- Department: {student['department']}
- Total Classes: {student['total_classes']}
- Present: {student['present_classes']}
- Absent: {student['absent_classes']}
- Attendance: {student['percentage']}%
- Status: CRITICAL (Below 60%)

⚠️ WARNING: Your attendance is critically low. Immediate action is required.

Please meet with your HOD to discuss this matter urgently.

Best Regards,
Sethupathy Government Arts College
Ramanathapuram
"""
                elif student['status'] == 'Warning':
                    body = f"""Dear {student['name']},

This is a notice regarding your attendance status.

Your Details:
- Student ID: {student['student_id']}
- Year: {student['year']}
- Department: {student['department']}
- Total Classes: {student['total_classes']}
- Present: {student['present_classes']}
- Absent: {student['absent_classes']}
- Attendance: {student['percentage']}%
- Status: WARNING (60-74%)

⚠️ Your attendance needs improvement to meet the 75% requirement.

Please ensure regular attendance to avoid academic issues.

Best Regards,
Sethupathy Government Arts College
Ramanathapuram
"""
                else:
                    body = f"""Dear {student['name']},

This is your attendance report.

Your Details:
- Student ID: {student['student_id']}
- Year: {student['year']}
- Department: {student['department']}
- Total Classes: {student['total_classes']}
- Present: {student['present_classes']}
- Absent: {student['absent_classes']}
- Attendance: {student['percentage']}%
- Status: GOOD

✓ Your attendance is satisfactory. Keep up the good work!

Best Regards,
Sethupathy Government Arts College
Ramanathapuram
"""
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Attach PDF
                with open(filepath, 'rb') as f:
                    attach = MIMEApplication(f.read(), _subtype='pdf')
                    attach.add_header('Content-Disposition', 'attachment',
                                    filename=f"Attendance_{student['student_id']}.pdf")
                    msg.attach(attach)
                
                # Send email
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
                
                self.email_log.insert(tk.END, f"[SUCCESS] {student['name']} ({student['email']})\n")
                success_count += 1
                
            except Exception as e:
                self.email_log.insert(tk.END, f"[FAIL] {student['name']}: {str(e)}\n")
                fail_count += 1
            
            # Update UI
            self.email_log.see(tk.END)
            self.root.update()
        
        # Summary
        self.email_log.insert(tk.END, f"\n{'='*80}\n")
        self.email_log.insert(tk.END, f"Bulk email completed!\n")
        self.email_log.insert(tk.END, f"Success: {success_count} | Failed: {fail_count}\n")
        self.email_log.insert(tk.END, f"{'='*80}\n\n")
        
        messagebox.showinfo("Complete", f"Emails sent!\n\nSuccess: {success_count}\nFailed: {fail_count}")
    
    def create_analytics_tab(self):
        """Enhanced Analytics with Year and Department breakdown"""
        analytics_frame = tk.Frame(self.analytics_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        analytics_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(analytics_frame, text="Analytics Dashboard", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=15)
        
        tk.Button(analytics_frame, text="🔄 Refresh Analytics", font=("Arial", 10, "bold"),
                 bg="#CC0000", fg="white", command=self.refresh_analytics,
                 cursor="hand2").pack(pady=10)
        
        self.analytics_display = tk.Frame(analytics_frame, bg="#ffffff")
        self.analytics_display.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.refresh_analytics()
    
    def refresh_analytics(self):
        for widget in self.analytics_display.winfo_children():
            widget.destroy()
        
        stats = self.system.get_statistics()
        if not stats or stats['total_students'] == 0:
            tk.Label(self.analytics_display, text="No data available",
                    font=("Arial", 12), bg="#ffffff").pack(pady=20)
            return
        
        # Summary cards
        cards_frame = tk.Frame(self.analytics_display, bg="#ffffff")
        cards_frame.pack(fill="x", pady=20)
        
        # Total students
        card1 = tk.Frame(cards_frame, bg="#007bff", relief="raised", borderwidth=2)
        card1.pack(side="left", padx=15, pady=10, ipadx=25, ipady=15)
        tk.Label(card1, text="Total Students", font=("Arial", 11, "bold"),
                bg="#007bff", fg="white").pack()
        tk.Label(card1, text=str(stats['total_students']), font=("Arial", 22, "bold"),
                bg="#007bff", fg="white").pack()
        
        # Average
        card2 = tk.Frame(cards_frame, bg="#17a2b8", relief="raised", borderwidth=2)
        card2.pack(side="left", padx=15, pady=10, ipadx=25, ipady=15)
        tk.Label(card2, text="Average Attendance", font=("Arial", 11, "bold"),
                bg="#17a2b8", fg="white").pack()
        tk.Label(card2, text=f"{stats['average_percentage']}%", font=("Arial", 22, "bold"),
                bg="#17a2b8", fg="white").pack()
        
        # Good
        card3 = tk.Frame(cards_frame, bg="#28a745", relief="raised", borderwidth=2)
        card3.pack(side="left", padx=15, pady=10, ipadx=25, ipady=15)
        tk.Label(card3, text="Good (≥75%)", font=("Arial", 11, "bold"),
                bg="#28a745", fg="white").pack()
        tk.Label(card3, text=str(stats['good_count']), font=("Arial", 22, "bold"),
                bg="#28a745", fg="white").pack()
        
        # Warning
        card4 = tk.Frame(cards_frame, bg="#ff8c00", relief="raised", borderwidth=2)
        card4.pack(side="left", padx=15, pady=10, ipadx=25, ipady=15)
        tk.Label(card4, text="Warning (60-74%)", font=("Arial", 11, "bold"),
                bg="#ff8c00", fg="white").pack()
        tk.Label(card4, text=str(stats['warning_count']), font=("Arial", 22, "bold"),
                bg="#ff8c00", fg="white").pack()
        
        # Critical
        card5 = tk.Frame(cards_frame, bg="#dc3545", relief="raised", borderwidth=2)
        card5.pack(side="left", padx=15, pady=10, ipadx=25, ipady=15)
        tk.Label(card5, text="Critical (<60%)", font=("Arial", 11, "bold"),
                bg="#dc3545", fg="white").pack()
        tk.Label(card5, text=str(stats['critical_count']), font=("Arial", 22, "bold"),
                bg="#dc3545", fg="white").pack()
        
        # Year distribution
        year_frame = tk.LabelFrame(self.analytics_display, text="Distribution by Year",
                                   font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=15)
        year_frame.pack(fill="x", padx=10, pady=10)
        
        for year in self.years:
            count = stats['year_distribution'].get(year, 0)
            pct = (count / stats['total_students'] * 100) if stats['total_students'] > 0 else 0
            
            row = tk.Frame(year_frame, bg="#ffffff")
            row.pack(fill="x", pady=5)
            
            tk.Label(row, text=f"{year}:", font=("Arial", 11, "bold"),
                    bg="#ffffff", width=12, anchor="w").pack(side="left")
            
            bar_frame = tk.Frame(row, bg="#e9ecef", height=25, width=400)
            bar_frame.pack(side="left", padx=10)
            bar_frame.pack_propagate(False)
            
            if count > 0:
                bar_width = int(400 * pct / 100)
                tk.Frame(bar_frame, bg="#007bff", width=bar_width).pack(side="left", fill="y")
            
            tk.Label(row, text=f"{count} ({pct:.1f}%)",
                    font=("Arial", 10), bg="#ffffff").pack(side="left", padx=10)
        
        # Department statistics
        dept_frame = tk.LabelFrame(self.analytics_display, text="Department Statistics",
                                   font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=15)
        dept_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollable frame for departments
        canvas = tk.Canvas(dept_frame, bg="#ffffff", height=250)
        scrollbar = ttk.Scrollbar(dept_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Department data
        for dept, count, avg_pct in stats['department_stats']:
            row = tk.Frame(scrollable_frame, bg="#ffffff", relief="groove", borderwidth=1)
            row.pack(fill="x", pady=3, padx=5)
            
            tk.Label(row, text=dept, font=("Arial", 10, "bold"),
                    bg="#ffffff", width=45, anchor="w").pack(side="left", padx=5)
            
            tk.Label(row, text=f"Students: {count}", font=("Arial", 9),
                    bg="#ffffff", width=15).pack(side="left", padx=5)
            
            avg_color = 'green' if avg_pct >= 75 else 'orange' if avg_pct >= 60 else 'red'
            tk.Label(row, text=f"Avg: {avg_pct:.2f}%", font=("Arial", 9, "bold"),
                    bg="#ffffff", fg=avg_color, width=12).pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_settings_tab(self):
        settings_frame = tk.Frame(self.settings_tab, bg="#ffffff", relief="ridge", borderwidth=2)
        settings_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        tk.Label(settings_frame, text="System Settings", font=("Arial", 16, "bold"),
                bg="#ffffff", fg="#CC0000").pack(pady=15)
        
        # Email config
        email_config = tk.LabelFrame(settings_frame, text="Email Configuration",
                                     font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=20)
        email_config.pack(padx=20, pady=10, fill="x")
        
        tk.Label(email_config, text="For Gmail, use App Password (not regular password)",
                font=("Arial", 9, "italic"), bg="#ffffff", fg="gray").grid(row=0, column=0, columnspan=2, pady=5)
        
        tk.Label(email_config, text="Sender Email:", font=("Arial", 11),
                bg="#ffffff").grid(row=1, column=0, sticky="w", pady=10)
        self.sender_email_entry = tk.Entry(email_config, font=("Arial", 11), width=40)
        self.sender_email_entry.grid(row=1, column=1, padx=10, pady=10)
        if self.sender_email:
            self.sender_email_entry.insert(0, self.sender_email)
        
        tk.Label(email_config, text="App Password:", font=("Arial", 11),
                bg="#ffffff").grid(row=2, column=0, sticky="w", pady=10)
        self.sender_password_entry = tk.Entry(email_config, font=("Arial", 11), width=40, show="*")
        self.sender_password_entry.grid(row=2, column=1, padx=10, pady=10)
        if self.sender_password:
            self.sender_password_entry.insert(0, self.sender_password)
        
        tk.Label(email_config, text="HOD Email:", font=("Arial", 11),
                bg="#ffffff").grid(row=3, column=0, sticky="w", pady=10)
        self.hod_email_entry = tk.Entry(email_config, font=("Arial", 11), width=40)
        self.hod_email_entry.grid(row=3, column=1, padx=10, pady=10)
        if self.hod_email:
            self.hod_email_entry.insert(0, self.hod_email)
        
        tk.Label(email_config, text="Threshold %:", font=("Arial", 11),
                bg="#ffffff").grid(row=4, column=0, sticky="w", pady=10)
        self.threshold_entry = tk.Entry(email_config, font=("Arial", 11), width=40)
        self.threshold_entry.grid(row=4, column=1, padx=10, pady=10)
        self.threshold_entry.insert(0, "75")
        
        tk.Button(email_config, text="💾 Save Configuration", font=("Arial", 11, "bold"),
                 bg="#CC0000", fg="white", command=self.save_email_config,
                 cursor="hand2").grid(row=5, column=1, pady=15)
        
        # Status thresholds info
        info_frame = tk.LabelFrame(settings_frame, text="Attendance Status Thresholds",
                                   font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=15)
        info_frame.pack(padx=20, pady=10, fill="x")
        
        tk.Label(info_frame, text="🟢 Good: 75% and above", font=("Arial", 11),
                bg="#ffffff", fg="green", anchor="w").pack(fill="x", pady=5)
        tk.Label(info_frame, text="🟠 Warning: 60% to 74%", font=("Arial", 11),
                bg="#ffffff", fg="orange", anchor="w").pack(fill="x", pady=5)
        tk.Label(info_frame, text="🔴 Critical: Below 60%", font=("Arial", 11),
                bg="#ffffff", fg="red", anchor="w").pack(fill="x", pady=5)
        
        # Backup
        backup_frame = tk.LabelFrame(settings_frame, text="Database Backup",
                                     font=("Arial", 12, "bold"), bg="#ffffff", padx=20, pady=20)
        backup_frame.pack(padx=20, pady=10, fill="x")
        
        tk.Button(backup_frame, text="💾 Create Backup", font=("Arial", 11, "bold"),
                 bg="#28a745", fg="white", width=20, command=self.create_backup_action,
                 cursor="hand2").pack(pady=10)
        
        self.backup_status = tk.Label(backup_frame, text="No backup yet",
                                     font=("Arial", 10), bg="#ffffff", fg="gray")
        self.backup_status.pack(pady=5)
    
    def save_email_config(self):
        self.sender_email = self.sender_email_entry.get().strip()
        self.sender_password = self.sender_password_entry.get().strip()
        self.hod_email = self.hod_email_entry.get().strip()
        
        try:
            threshold = float(self.threshold_entry.get())
        except:
            threshold = 75.0
        
        if self.sender_email and self.sender_password:
            self.system.save_email_settings(self.sender_email, self.sender_password,
                                           self.hod_email, threshold)
            messagebox.showinfo("Success", "Email settings saved successfully!")
        else:
            messagebox.showwarning("Warning", "Please fill sender email and password!")
    
    def create_backup_action(self):
        success, msg = self.system.create_backup()
        if success:
            self.backup_status.config(text=f"Last backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                     fg="green")
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AttendanceGUI(root)
        
        print("="*70)
        print("Attendance Management System")
        print("Sethupathy Government Arts College, Ramanathapuram")
        print("="*70)
        print("System started successfully!")
        print("="*70)
        
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication closed")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
