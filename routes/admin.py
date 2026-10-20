from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.db import fetch_all, fetch_one, get_db_connection, generate_csrf_token, verify_csrf_token

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/dashboard')
def dashboard():
    if not session.get('user_id'):
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    if not user or user['role'] != 'admin':
        flash('Access denied. Admin account required.', 'warning')
        return redirect(url_for('home'))

    total_patients = fetch_one('SELECT COUNT(*) AS count FROM patients')['count']
    total_doctors = fetch_one('SELECT COUNT(*) AS count FROM doctors')['count']
    total_appointments = fetch_one('SELECT COUNT(*) AS count FROM appointments')['count']
    pending_doctors = fetch_one('SELECT COUNT(*) AS count FROM doctors WHERE verification_status = "pending"')['count']
    recent_appointments = fetch_all('''
        SELECT a.*, p.user_id, u.full_name as patient_name, d.speciaLization, du.full_name as doctor_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        JOIN doctors d On d.id = a.doctor_id
        JOIN users du ON du.id = d.user_id
        ORDER BY a.created_at DESC LIMIT 10
    ''')
    return render_template(
        'dashboard_admin.html',
        user=user,
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_appointments=total_appointments,
        pending_doctors=pending_doctors,
        recent_appointments=recent_appointments,
        csrf_token=generate_csrf_token(),
    )


@admin_bp.route('/admin/verify-doctor/<int:doctor_id>', methods=['POST'])
def verify_doctor(doctor_id):
    if not session.get('user_id'):
        flash('Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    user = fetch_one('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    if user['role'] != 'admin':
        flash('Access denied. Admin account required.', 'warning')
        return redirect(url_for('home'))

    token = request.form.get('csrf_token')
    if not verify_csrf_token(token):
        flash('Invalid security token.', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = get_db_connection()
    conn.execute('UPDATE doctors SET verification_status = ? WHERE id = ?', ('verified', doctor_id))
    conn.commit()
    conn.close()
    flash('Doctor verification updated.', 'success')
    return redirect(url_for('admin.dashboard'))

