import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from config import DATABASE_PATH
from models.db import fetch_one, get_db_connection, generate_csrf_token, verify_csrf_token


auth_bp = Flask(__name__)

auth_bp = Flask(__name__)


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'patient')
        token = request.form.get('csrf_token')

        if not verify_csrf_token(token):
            flash('Invalid security token.', 'danger')
            return redirect(url_for('auth.register'))

        if not all([full_name, username, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html', csrf_token=generate_csrf_token())

        if fetch_one('SELECT id FROM users WHERE email = ?', (email,)):
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html', csrf_token=generate_csrf_token())

        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.execute(
            'INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)',
            (username, email, password_hash, role, full_name, request.form.get('phone') or '')
        )
        conn.commit()
        user_id = cursor.lastrowid

        if role == 'patient':
            conn.execute(
                'INSERT INTO patients (user_id, date_of_birth, gender, blood_group, address, emergency_contact) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, request.form.get('date_of_birth') or None, request.form.get('gender') or None, request.form.get('blood_group') or None, request.form.get('address') or None, request.form.get('emergency_contact') or None)
            )
        elif role == 'doctor':
            conn.execute(
                'INSERT INTO doctors (user_id, specialization, qualification, experience_years, bio, verification_status) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, request.form.get('specialization') or 'General Medicine', request.form.get('qualification') or 'MD', request.form.get('experience_years') or 1, request.form.get('bio') or 'Experienced doctor.', 'pending')
            )
        conn.commit()
        conn.close()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', csrf_token=generate_csrf_token())


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        token = request.form.get('csrf_token')

        if not verify_csrf_token(token):
            flash('Invalid security token.', 'danger')
            return redirect(url_for('auth.login'))

        user = fetch_one('SELECT * FROM users WHERE email = ?', (email,))
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('Login successful.', 'success')
            if user['role'] == 'patient':
                return redirect(url_for('patient.dashboard'))
            if user['role'] == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
        flash('Invalid email or password.', 'danger')
        return render_template('login.html', csrf_token=generate_csrf_token())

    return render_template('login.html', csrf_token=generate_csrf_token())

