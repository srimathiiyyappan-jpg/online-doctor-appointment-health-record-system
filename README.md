# Online Doctor Appointment and Health Record System

A responsive healthcare web application built with Python Flask, SQLite, and Bootstrap 5 for a college mini-project.

## Project Overview
This project allows patients to book appointments with doctors, maintain digital health records, view prescriptions, and manage their medical history in a secure, role-based environment. Doctors can review patient appointments, update records, and add prescriptions. Admins can manage accounts and monitor system activity.

## Features
- User registration and login for patients, doctors, and admin
- Secure password hashing with Flask session management
- Doctor search by name and specialization
- Appointment booking with duplicate-slot prevention
- Appointment tracking and status updates
- Prescription and medical history management
- Secure file upload for medical reports
- Responsive dashboard and healthcare-themed UI
- SQLite database with sample demo data
- Basic automated tests for core flows

## Technology Stack
- Frontend: HTML, CSS, JavaScript, Bootstrap 5
- Backend: Python Flask
- Database: SQLite
- Security: Werkzeug password hashing, session checks, CSRF validation
- Testing: Pytest

## Folder Structure
```text
online-doctor-appointment-health-record-system/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
├── instance/
├── database/
│   └── init_db.py
├── models/
│   ├── __init__.py
│   └── db.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── patient.py
│   ├── doctor.py
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── register.html
│   ├── login.html
│   ├── doctor_list.html
│   ├── doctor_profile.html
│   ├── appointment_booking.html
│   ├── appointment_history.html
│   ├── health_records.html
│   ├── prescription.html
│   ├── dashboard_patient.html
│   ├── dashboard_doctor.html
│   ├── dashboard_admin.html
│   └── profile.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
├── uploads/
│   └── .gitkeep
├── tests/
│   └── test_app.py
└── .env.example
```

## Database Design
The SQLite app includes these tables:
- users
- doctors
- patients
- appointments
- medical_records
- prescriptions
- doctor_availability

Foreign keys and timestamps are used to maintain relational integrity. Passwords are never stored as plain text.

## Setup Instructions (Windows)
1. Install Python 3.11+
2. Open Command Prompt in the project folder
3. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Initialize the database:
   ```bash
   python database/init_db.py
   ```
6. Run the app:
   ```bash
   python app.py
   ```
7. Open in the browser:
   ```text
   http://127.0.0.1:5000/
   ```

## VS Code Run Commands
Use these commands in the VS Code terminal:
```bash
cd online-doctor-appointment-health-record-system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python database/init_db.py
python app.py
```

## Demo Accounts
Username | Role | Password
--- | --- | ---
admin@medcare.local | Admin | admin123
drsmith@medcare.local | Doctor | doctor123
jane@medcare.local | Patient | patient123

## Workflow Testing
### Patient flow
1. Register a patient account
2. Log in as patient
3. Search for a doctor
4. Open doctor profile and book an appointment
5. View appointment history
6. Upload a report under health records
7. Review prescriptions

### Doctor flow
1. Log in as `drsmith@medcare.local`
2. Open doctor dashboard
3. View pending appointments
4. Approve or reject requests
5. Add prescription details

### Admin flow
1. Log in as `admin@medcare.local`
2. View application overview
3. Verify doctor accounts
4. Manage doctor specializations and appointments

## Security Notes
- Passwords are stored using Werkzeug hashing
- All authenticated routes are protected
- Role-based access control is enforced
- Uploaded files are validated by extension and size
- This is an educational prototype and not a certified clinical system

## Future Enhancements
- Email notifications
- Online payment integration
- Video consultation support
- Better audit logs and encryption
- Advanced patient reporting

## Screenshots
Add screenshots in the `screenshots/` folder and reference them here.

## GitHub Repository Description
Online Doctor Appointment and Health Record System built with Python Flask, SQLite, Bootstrap 5, and role-based healthcare workflows for a mini-project.

## GitHub Topics
`flask` `python` `healthcare` `sqlite` `bootstrap` `mini-project`

## Deployment and Security Disclaimer
This prototype is designed for educational use only. It should not be used for real clinical care or patient data handling without a proper security review, legal authorization, and production-grade deployment setup.
