import os
import sqlite3

from flask import session
from werkzeug.security import generate_password_hash

from config import DATABASE_PATH


def ensure_directory(path):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_db_connection():
    ensure_directory(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def fetch_all(query, params=()):
    conn = get_db_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_one(query, params=()):
    conn = get_db_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute_db(query, params=()):
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor
    finally:
        conn.close()


def generate_csrf_token():
    token = session.get('csrf_token')
    if not token:
        import secrets
        token = secrets.token_hex(16)
        session['csrf_token'] = token
    return token


def verify_csrf_token(token):
    return bool(token and token == session.get('csrf_token'))


def init_db():
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient', 'doctor', 'admin')),
            full_name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            specialization TEXT,
            qualification TEXT,
            experience_years INTEGER DEFAULT 0,
            bio TEXT,
            verification_status TEXT DEFAULT 'pending' CHECK(verification_status IN ('pending', 'verified', 'rejected')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            date_of_birth TEXT,
            gender TEXT,
            blood_group TEXT,
            address TEXT,
            emergency_contact TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS doctor_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            slot_duration INTEGER DEFAULT 30,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed', 'cancelled')),
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER,
            record_type TEXT,
            title TEXT NOT NULL,
            description TEXT,
            file_name TEXT,
            file_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_id INTEGER,
            diagnosis TEXT,
            medicine TEXT,
            instructions TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id),
            FOREIGN KEY(appointment_id) REFERENCES appointments(id)
        );
    ''')

    seed_demo_data(conn)
    conn.close()


def seed_demo_data(conn):
    def seed_user(username, email, password, role, full_name, phone=''):
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            return existing[0]
        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            'INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)',
            (username, email, password_hash, role, full_name, phone)
        )
        return cursor.lastrowid

    admin_id = seed_user('admin', 'admin@medcare.local', 'admin123', 'admin', 'Admin User', '5550000001')
    doctor_user_id = seed_user('drsmith', 'drsmith@medcare.local', 'doctor123', 'doctor', 'Dr. Sarah Smith', '5550000002')
    patient_user_id = seed_user('jane', 'jane@medcare.local', 'patient123', 'patient', 'Jane Miller', '5550000003')

    existing_doctor = conn.execute('SELECT id FROM doctors WHERE user_id = ?', (doctor_user_id,)).fetchone()
    if not existing_doctor:
        conn.execute(
            'INSERT INTO doctors (user_id, specialization, qualification, experience_years, bio, verification_status) VALUES (?, ?, ?, ?, ?, ?)',
            (doctor_user_id, 'Cardiology', 'MD, Cardiology', 12, 'Experienced cardiologist supporting preventive and acute care.', 'verified')
        )

    existing_patient = conn.execute('SELECT id FROM patients WHERE user_id = ?', (patient_user_id,)).fetchone()
    if not existing_patient:
        conn.execute(
            'INSERT INTO patients (user_id, date_of_birth, gender, blood_group, address, emergency_contact) VALUES (?, ?, ?, ?, ?, ?)',
            ('2021-02-15', 'female', 'O+', '123 Wellness Street, Boston', '5550000004')
        )

    doctor_id = conn.execute('SELECT id FROM doctors WHERE user_id = ?', (doctor_user_id,)).fetchone()[0]
    patient_id = conn.execute('SELECT id FROM patients WHERE user_id = ?', (patient_user_id,)).fetchone()[0]

    availability = conn.execute('SELECT id FROM doctor_availability WHERE doctor_id = ?', (doctor_id,)).fetchone()
    if not availability:
        conn.execute(
            'INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, slot_duration) VALUES (?, ?, ?, ?, ?)',
            (doctor_id, 'Monday', '09:00', '12:00', 30)
        )
        conn.execute(
            'INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, slot_duration) VALUES (?, ?, ?, ?, ?)',
            (doctor_id, 'Wednesday', '14:00', '17:00', 30)
        )

    existing_appointment = conn.execute(
        'SELECT id FROM appointments WHERE patient_id = ? AND doctor_id = ?',
        (patient_id, doctor_id)
    ).fetchone()
    if not existing_appointment:
        conn.execute(
            'INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, notes) VALUES (?, ?, ?, ?, ?, ?)',
            (patient_id, doctor_id, '2026-10-25', '10:00', 'approved', 'Routine consultation')
        )

    existing_record = conn.execute('SELECT id FROM medical_records WHERE patient_id = ? AND title = ?', (patient_id, 'Annual Checkup')).fetchone()
    if not existing_record:
        conn.execute(
            'INSERT INTO medical_records (patient_id, doctor_id, record_type, title, description) VALUES (?, ?, ?, ?, ?)',
            (patient_id, doctor_id, 'report', 'Annual Checkup', 'Routine wellness evaluation.')
        )

    existing_prescription = conn.execute('SELECT id FROM prescriptions WHERE patient_id = ? AND doctor_id = ?', (patient_id, doctor_id)).fetchone()
    if not existing_prescription:
        conn.execute(
            'INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, diagnosis, medicine, instructions) VALUES (?, ?, ?, ?, ?, ?)',
            (patient_id, doctor_id, None, 'Mild hypertension', 'Lisinopril 10mg', 'Take one tablet daily in the morning.')
        )

    conn.commit()

