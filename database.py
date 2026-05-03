import sqlite3
import pandas as pd

DB_NAME = "medical_system_v2.db"

def init_db():
    """Initializes the relational database with linked tables, views, and triggers."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Base Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS departments (dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors (doctor_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, dept_id INTEGER, FOREIGN KEY (dept_id) REFERENCES departments (dept_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS patients (patient_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, dob TEXT, blood_group TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (report_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, doctor_id INTEGER, raw_text TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (patient_id) REFERENCES patients (patient_id), FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vitals (vital_id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER, blood_pressure TEXT, heart_rate INTEGER, FOREIGN KEY (report_id) REFERENCES reports (report_id))''')
    
    # 2. Advanced Feature: Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            table_affected TEXT NOT NULL,
            record_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Advanced Feature: Database Trigger
    # This automatically writes to the audit_logs table whenever a report is inserted
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS log_new_report 
        AFTER INSERT ON reports
        BEGIN
            INSERT INTO audit_logs (action_type, table_affected, record_id) 
            VALUES ('INSERT', 'reports', NEW.report_id);
        END;
    ''')
    
    # 4. Advanced Feature: Database View
    # This pre-compiles our complex JOIN so the frontend doesn't have to process it
    cursor.execute('''
        CREATE VIEW IF NOT EXISTS patient_dashboard_view AS
        SELECT 
            p.patient_id,
            p.name AS patient_name,
            r.upload_date,
            d.name AS doctor,
            v.blood_pressure,
            v.heart_rate,
            r.raw_text
        FROM patients p
        JOIN reports r ON p.patient_id = r.patient_id
        JOIN doctors d ON r.doctor_id = d.doctor_id
        JOIN vitals v ON r.report_id = v.report_id;
    ''')
    
    # Seed initial data if empty
    cursor.execute("SELECT COUNT(*) FROM departments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO departments (dept_name) VALUES ('Cardiology'), ('General Medicine')")
        cursor.execute("INSERT INTO doctors (name, dept_id) VALUES ('Dr. Aditya Srivastava', 1)")
        cursor.execute("INSERT INTO patients (name, dob, blood_group) VALUES ('John Doe', '1990-05-14', 'O+')")
        
    conn.commit()
    conn.close()

def add_full_report(patient_id, doctor_id, raw_text, bp, hr):
    """Inserts raw report and extracted structured vitals transactionally."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO reports (patient_id, doctor_id, raw_text) VALUES (?, ?, ?)", (patient_id, doctor_id, raw_text))
    report_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO vitals (report_id, blood_pressure, heart_rate) VALUES (?, ?, ?)", (report_id, bp, hr))
    
    conn.commit()
    conn.close()

def get_patient_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    conn.close()
    return df

def get_doctor_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM doctors", conn)
    conn.close()
    return df

def get_structured_history(patient_id):
    """Now querying the SQL View instead of writing raw JOINs."""
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT upload_date, doctor, blood_pressure, heart_rate, raw_text FROM patient_dashboard_view WHERE patient_id = {patient_id} ORDER BY upload_date DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_or_create_patient(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE name = ?", (name,))
    result = cursor.fetchone()
    if result:
        p_id = result[0]
    else:
        cursor.execute("INSERT INTO patients (name, dob, blood_group) VALUES (?, 'Unknown', 'Unknown')", (name,))
        p_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return p_id

def get_or_create_doctor(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT doctor_id FROM doctors WHERE name = ?", (name,))
    result = cursor.fetchone()
    if result:
        d_id = result[0]
    else:
        cursor.execute("INSERT INTO doctors (name, dept_id) VALUES (?, 2)", (name,))
        d_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return d_id

if __name__ == "__main__":
    init_db()