from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from models.db import execute_db, fetch_all, fetch_one, get_db_connection, generate_csrf_token, verify_csrf_token
from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER
import os

patient_bp = Blueprint('patient', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@patient_bp.route('/patient/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))
    patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user_id,))
    upcoming = fetch_all('''
        SELECT a.*, d.specialization, u.full_name as doctor_name
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE a.patient_id = ? AND a.status IN ('pending', 'approved')
        ORDER BY a.appointment_date, a.appointment_time
    ''', (patient['id'],)) if patient else []
    records = fetch_all('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY created_at DESC LIMIT 5', (patient['id'],)) if patient else []
    return render_template('dashboard_patient.html', user=user, patient=patient, appointments=upcoming, records=records)


@patient_bp.route('/patient/book/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if not session.get('user_id'):
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    if user['role'] != 'patient':
        flash('Only patients can book appointments.', 'warning')
        return redirect(url_for('home'))

    patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (session['user_id'],))
    doctor = fetch_one('''
        SELECT d.*, u.full_name, u.email, u.phone
        FROM doctors d JOIN users u ON u.id = d.user_id
        WHERE d.id = ?
    ''', (doctor_id,))
    if not doctor:
        flash('Doctor not found.', 'danger')
        return redirect(url_for('doctors_list'))

    availability = fetch_all('SELECT * FROM doctor_availability WHERE doctor_id = ? ORDER BY day_of_week, start_time', (doctor_id,))

    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not verify_csrf_token(token):
            flash('Invalid security token.', 'danger')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))

        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        notes = request.form.get('notes', '').strip()

        if not appointment_date or not appointment_time:
            flash('Appointment date and time are required.', 'danger')
            return render_template('appointment_booking.html', doctor=doctor, availability=availability, csrf_token=generate_csrf_token())

        conflict = fetch_one('''
            SELECT id FROM appointments
            WHERE patient_id = ? AND doctor_id = ? AND appointment_date = ? AND appointment_time = ? AND status NOT IN ('cancelled', 'rejected')
        ''', (patient['id'], doctor_id, appointment_date, appointment_time))
        if conflict:
            flash('This slot is already booked for you. Please choose another time.', 'danger')
            return render_template('appointment_booking.html', doctor=doctor, availability=availability, csrf_token=generate_csrf_token())

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, notes)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (patient['id'], doctor_id, appointment_date, appointment_time, notes))
        conn.commit()
        conn.close()
        flash('Appointment request submitted successfully.', 'success')
        return redirect(url_for('patient.appointment_history'))

    return render_template('appointment_booking.html', doctor=doctor, availability=availability, csrf_token=generate_csrf_token())


@patient_bp.route('/patient/history')
def appointment_history():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user_id,))
    if not patient:
        flash('Patient profile not found.', 'warning')
        return redirect(url_for('profile'))

    appointments = fetch_all('''
        SELECT a.*, u.full_name as doctor_name, d.specialization
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (patient['id'],))
    return render_template('appointment_history.html', appointments=appointments)


@patient_bp.route('/patient/records', methods=['GET', 'POST'])
def health_records():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user_id,))
    if not patient:
        flash('Patient profile not found.', 'warning')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not verify_csrf_token(token):
            flash('Invalid security token.', 'danger')
            return redirect(url_for('patient.health_records'))

        title = request.form.get('title', '').strip()
        record_type = request.form.get('record_type', 'report').strip()
        description = request.form.get('description', '').strip()
        file = request.files.get('report_file')

        if not title:
            flash('Record title is required.', 'danger')
            return redirect(url_for('patient.health_records'))

        file_path = None
        file_name = None
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Unsupported file type. Allowed: PDF, JPG, JPEG, PNG', 'danger')
                return redirect(url_for('patient.health_records'))
            if file.content_length and file.content_length > 2 * 1024 * 1024:
                flash('File size must be under 2MB.', 'danger')
                return redirect(url_for('patient.health_records'))
            filename = secure_filename(file.filename)
            file_name = filename
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO medical_records (patient_id, doctor_id, record_type, title, description, file_name, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (patient['id'], None, record_type, title, description, file_name, file_path))
        conn.commit()
        conn.close()
        flash('Medical record uploaded successfully.', 'success')
        return redirect(url_for('patient.health_records'))

    records = fetch_all('SELECT * FROM medical_records WHERE patient_id = ? ORDER BY created_at DESC', (patient['id'],))
    return render_template('health_records.html', records=records, csrf_token=generate_csrf_token())


@patient_bp.route('/patient/prescriptions')
def prescriptions():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user_id,))
    if not patient:
        flash('Patient profile not found.', 'warning')
        return redirect(url_for('profile'))

    prescriptions = fetch_all('''
        SELECT p.*, u.full_name as doctor_name
        FROM prescriptions p
        JOIN doctors d ON d.id = p.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE p.patient_id = ?
        ORDER BY p.created_at DESC
    ''', (patient['id'],))
    return render_template('prescription.html', prescriptions=prescriptions)

