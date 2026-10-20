from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.db import fetch_all, fetch_one, get_db_connection, generate_csrf_token, verify_csrf_token


doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/doctor/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))
    if user['role'] != 'doctor':
        flash('Access denied. Doctor account required.', 'warning')
        return redirect(url_for('home'))

    doctor = fetch_one('SELECT * FROM doctors WHERE user_id = ?', (user_id,))
    pending = fetch_all('''
        SELECT a.*, p.user_id, u.full_name as patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id = ? AND a.status = 'pending'
        ORDER BY a.appointment_date, a.appointment_time
    ''', (doctor['id'],)) if doctor else []
    upcoming = fetch_all('''
        SELECT a.*, u.full_name as patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id = ? AND a.status IN ('approved', 'completed')
        ORDER BY a.appointment_date, a.appointment_time
    ''', (doctor['id'],)) if doctor else []
    return render_template('dashboard_doctor.html', user=user, doctor=doctor, pending=pending, upcoming=upcoming)


@doctor_bp.route('/doctor/appointments/<int:appointment_id>/<action>', methods=['POST'])
def update_appointment(appointment_id, action):
    if not session.get('user_id'):
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    token = request.form.get('csrf_token')
    if not verify_csrf_token(token):
        flash('Invalid security token.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    appointment = fetch_one('SELECT * FROM appointments WHERE id = ?', (appointment_id,))
    if not appointment:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    doctor = fetch_one('SELECT * FROM doctors WHERE user_id = ?', (session['user_id'],))
    if not doctor or appointment['doctor_id'] != doctor['id']:
        flash('You can only manage your own appointments.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    allowed = {'approve': 'approved', 'reject': 'rejected', 'complete': 'completed'}
    if action not in allowed:
        flash('Unknown appointment action.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    conn = get_db_connection()
    conn.execute('UPDATE appointments SET status = ? WHERE id = ?', (allowed[action], appointment_id))
    conn.commit()
    conn.close()
    flash(f'Appointment {action}d successfully.', 'success')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/doctor/prescribe/<int:appointment_id>', methods=['GET', 'POST'])
def prescribe(appointment_id):
    if not session.get('user_id'):
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    if user['role'] != 'doctor':
        flash('Doctor account required.', 'warning')
        return redirect(url_for('home'))

    appointment = fetch_one('''
        SELECT a.*, p.user_id, u.full_name as patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.id = ?
    ''', (appointment_id,))
    doctor = fetch_one('SELECT * FROM doctors WHERE user_id = ?', (session['user_id'],))
    if not appointment or not doctor or appointment['doctor_id'] != doctor['id']:
        flash('Appointment not found or not assigned to you.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not verify_csrf_token(token):
            flash('Invalid security token.', 'danger')
            return redirect(url_for('doctor.prescribe', appointment_id=appointment_id))

        diagnosis = request.form.get('diagnosis', '').strip()
        medicine = request.form.get('medicine', '').strip()
        instructions = request.form.get('instructions', '').strip()

        if not diagnosis or not medicine:
            flash('Diagnosis and medicine are required.', 'danger')
            return render_template('prescription_form.html', appointment=appointment, csrf_token=generate_csrf_token())

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, diagnosis, medicine, instructions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (appointment['patient_id'], appointment['doctor_id'], appointment_id, diagnosis, medicine, instructions))
        conn.commit()
        conn.close()
        flash('Prescription saved successfully.', 'success')
        return redirect(url_for('doctor.dashboard'))

    return render_template('prescription_form.html', appointment=appointment, csrf_token=generate_csrf_token())

