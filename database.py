import sqlite3
import pandas as pd

DB_NAME = "medical_system_v2.db"

def init_db():
    """Initializes the relational database with linked tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Departments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT NOT NULL
        )
    ''')
    
    # 2. Doctors Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dept_id INTEGER,
            FOREIGN KEY (dept_id) REFERENCES departments (dept_id)
        )
    ''')
    
    # 3. Patients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT,
            blood_group TEXT
        )
    ''')
    
    # 4. Reports Table (Raw Data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            raw_text TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id)
        )
    ''')
    
    # 5. Vitals Table (Structured Data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vitals (
            vital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            blood_pressure TEXT,
            heart_rate INTEGER,
            FOREIGN KEY (report_id) REFERENCES reports (report_id)
        )
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
    
    cursor.execute(
        "INSERT INTO reports (patient_id, doctor_id, raw_text) VALUES (?, ?, ?)",
        (patient_id, doctor_id, raw_text)
    )
    report_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO vitals (report_id, blood_pressure, heart_rate) VALUES (?, ?, ?)",
        (report_id, bp, hr)
    )
    
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
    """JOIN query to pull structured data for the dashboard."""
    conn = sqlite3.connect(DB_NAME)
    query = f"""
        SELECT r.upload_date, d.name as doctor, v.blood_pressure, v.heart_rate, r.raw_text
        FROM reports r
        JOIN doctors d ON r.doctor_id = d.doctor_id
        JOIN vitals v ON r.report_id = v.report_id
        WHERE r.patient_id = {patient_id}
        ORDER BY r.upload_date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_or_create_patient(name):
    """Finds a patient by name, or creates a new one if they don't exist."""
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
    """Finds a doctor by name, or creates a new one in General Medicine."""
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