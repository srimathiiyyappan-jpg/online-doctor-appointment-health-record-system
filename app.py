import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

from config import BASE_DIR, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from models.db import get_db_connection, init_db, fetch_all, fetch_one, execute_db, generate_csrf_token, verify_csrf_token
from routes.auth import auth_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.admin import admin_bp


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    @app.context_processor
    def inject_session_user():
        user = None
        if session.get('user_id'):
            user = fetch_one("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        return {'current_user': user}

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('home'))

    @app.route('/profile')
    def profile():
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))

        user = fetch_one('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        if user['role'] == 'patient':
            patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user['id'],))
            return render_template('profile.html', user=user, patient=patient)
        if user['role'] == 'doctor':
            doctor = fetch_one('SELECT * FROM doctors WHERE user_id = ?', (user['id'],))
            return render_template('profile.html', user=user, doctor=doctor)
        return render_template('profile.html', user=user)

    @app.route('/doctors')
    def doctors_list():
        search = request.args.get('search', '').strip()
        specialization = request.args.get('specialization', '').strip()
        query = "SELECT d.*, u.full_name, u.email FROM doctors d JOIN users u ON u.id = d.user_id WHERE d.verification_status = 'verified'"
        params = []
        if search:
            query += " AND (u.full_name LIKE ? OR d.specialization LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        if specialization:
            query += " AND d.specialization LIKE ?"
            params.append(f'%{specialization}%')
        query += " ORDER BY u.full_name"
        doctors = fetch_all(query, params)
        return render_template('doctor_list.html', doctors=doctors, search=search, specialization=specialization)

    @app.route('/doctors/<int:doctor_id>')
    def doctor_profile(doctor_id):
        doctor = fetch_one('''
            SELECT d.*, u.full_name, u.email, u.phone
            FROM doctors d JOIN users u ON u.id = d.user_id
            WHERE d.id = ?
        ''', (doctor_id,))
        if not doctor:
            flash('Doctor not found.', 'danger')
            return redirect(url_for('doctors_list'))
        availability = fetch_all('SELECT * FROM doctor_availability WHERE doctor_id = ? ORDER BY day_of_week, start_time', (doctor_id,))
        return render_template('doctor_profile.html', doctor=doctor, availability=availability)

    @app.route('/profile/update', methods=['POST'])
    def update_profile():
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))

        token = request.form.get('csrf_token')
        if not verify_csrf_token(token):
            flash('Invalid security token. Please try again.', 'danger')
            return redirect(url_for('profile'))

        user_id = session['user_id']
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not full_name:
            flash('Full name is required.', 'danger')
            return redirect(url_for('profile'))

        conn = get_db_connection()
        conn.execute(
            'UPDATE users SET full_name = ?, phone = ? WHERE id = ?',
            (full_name, phone, user_id)
        )
        conn.commit()
        conn.close()

        role = fetch_one('SELECT role FROM users WHERE id = ?', (user_id,))['role']
        if role == 'patient':
            patient = fetch_one('SELECT * FROM patients WHERE user_id = ?', (user_id,))
            if patient:
                conn = get_db_connection()
                conn.execute(
                    'UPDATE patients SET date_of_birth = ?, gender = ?, blood_group = ?, address = ?, emergency_contact = ? WHERE user_id = ?',
                    (
                        request.form.get('date_of_birth') or None,
                        request.form.get('gender') or None,
                        request.form.get('blood_group') or None,
                        request.form.get('address') or None,
                        request.form.get('emergency_contact') or None,
                        user_id,
                    )
                )
                conn.commit()
                conn.close()
        elif role == 'doctor':
            doctor = fetch_one('SELECT * FROM doctors WHERE user_id = ?', (user_id,))
            if doctor:
                conn = get_db_connection()
                conn.execute(
                    'UPDATE doctors SET specialization = ?, qualification = ?, experience_years = ?, bio = ? WHERE user_id = ?',
                    (
                        request.form.get('specialization') or None,
                        request.form.get('qualification') or None,
                        request.form.get('experience_years') or 0,
                        request.form.get('bio') or None,
                        user_id,
                    )
                )
                conn.commit()
                conn.close()

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)

    init_db()
    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


