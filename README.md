# CampusRecruit

A full-stack web application built for the GDG NSUT Task 2 (Track B). This platform streamlines the college society recruitment process, allowing students to explore societies and apply, while giving admins a dedicated dashboard to manage applications.

## Tech Stack
* **Backend:** Python, Flask
* **Database:** SQLite (using Flask-SQLAlchemy)
* **Frontend:** HTML, Bootstrap, Jinja2 Templates
* **Authentication:** Flask-Login with Werkzeug password hashing

## Features Implemented
* **Relational Database:** Proper Foreign Key constraints between Users, Societies, and Applications.
* **Secure Authentication:** Passwords are mathematically hashed (not stored in plaintext).
* **Role-Based Access Control (RBAC):** Admin routes are strictly protected on the backend. A student attempting to access `/admin` will receive a 403 Forbidden error.
* **Dynamic Status Tracking:** Admins can dynamically accept or reject applications, which updates on the student's dashboard.

## How to Run Locally
1. Clone the repository.
2. Install dependencies: `pip install flask flask-sqlalchemy flask-login werkzeug`
3. Run the server: `python app.py`
4. Visit `http://127.0.0.1:5000` in your browser.
