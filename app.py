import os
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gdsc-college-recruitment-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


# -------------------------------------------------------------------
# 1. Database Schema
# -------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student' or 'admin'

    # Relationships
    managed_societies = db.relationship('Society', backref='admin', lazy=True)
    applications = db.relationship('Application', backref='student', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Society(db.Model):
    __tablename__ = 'societies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'Tech', 'Cultural', 'Sports'
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    applications = db.relationship('Application', backref='society', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Society {self.name} [{self.category}]>'


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    society_id = db.Column(db.Integer, db.ForeignKey('societies.id'), nullable=False)
    role_applied_for = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')  # 'Pending', 'Accepted', 'Rejected'
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Application {self.id}: User {self.student_id} -> Society {self.society_id} ({self.status})>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -------------------------------------------------------------------
# 2. Authentication & Role-Based Access Control (RBAC)
# -------------------------------------------------------------------

def admin_required(f):
    """
    Decorator to restrict route access strictly to users with the 'admin' role.
    Rejects normal students with HTTP 403 Forbidden.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------------
# 3. Application Routes
# -------------------------------------------------------------------

@app.route('/')
def index():
    """Home page listing all societies as Bootstrap cards."""
    societies = Society.query.order_by(Society.name.asc()).all()
    return render_template('index.html', societies=societies)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Standard user registration flow."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student').strip()

        # Basic validations
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if role not in ['student', 'admin']:
            role = 'student'

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        new_user = User(
            name=name,
            email=email,
            role=role
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(f'Account created successfully as {role.capitalize()}! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Standard user login flow."""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('admin_panel' if user.is_admin() else 'dashboard'))

        flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logs the user out and clears the session."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/apply/<int:society_id>', methods=['GET', 'POST'])
@login_required
def apply(society_id):
    """Form for a student to apply to a society."""
    society = db.session.get(Society, society_id)
    if not society:
        flash('Society not found.', 'danger')
        return redirect(url_for('index'))

    # Check for existing pending application to avoid duplicate spam
    existing_application = Application.query.filter_by(
        student_id=current_user.id,
        society_id=society.id,
        status='Pending'
    ).first()

    if existing_application:
        flash(f'You already have a pending application for {society.name} ({existing_application.role_applied_for}).', 'warning')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        role_applied_for = request.form.get('role_applied_for', '').strip()

        if not role_applied_for:
            flash('Please specify the role you are applying for.', 'danger')
            return render_template('apply.html', society=society)

        application = Application(
            student_id=current_user.id,
            society_id=society.id,
            role_applied_for=role_applied_for,
            status='Pending'
        )
        db.session.add(application)
        db.session.commit()

        flash(f'Successfully submitted application for {society.name} as {role_applied_for}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('apply.html', society=society)


@app.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard to see their applied societies and current statuses."""
    applications = Application.query.filter_by(student_id=current_user.id).order_by(Application.applied_at.desc()).all()
    return render_template('dashboard.html', applications=applications)


@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel to see all applications for societies managed by the current admin."""
    # Retrieve societies managed by the current admin
    managed_societies = Society.query.filter_by(admin_id=current_user.id).all()
    managed_society_ids = [s.id for s in managed_societies]

    applications = []
    if managed_society_ids:
        applications = Application.query.filter(
            Application.society_id.in_(managed_society_ids)
        ).order_by(Application.applied_at.desc()).all()

    return render_template(
        'admin.html',
        managed_societies=managed_societies,
        applications=applications
    )


@app.route('/admin/update_status/<int:application_id>', methods=['POST'])
@admin_required
def update_status(application_id):
    """Admin can update an application status to 'Accepted' or 'Rejected'."""
    application = db.session.get(Application, application_id)
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('admin_panel'))

    # Security check: Ensure this application belongs to a society managed by this admin
    if application.society.admin_id != current_user.id:
        flash('Unauthorized: You do not manage this society.', 'danger')
        abort(403)

    new_status = request.form.get('status', '').strip()
    if new_status in ['Accepted', 'Rejected', 'Pending']:
        application.status = new_status
        db.session.commit()
        flash(f"Application #{application.id} for {application.student.name} updated to '{new_status}'.", 'success')
    else:
        flash('Invalid status provided.', 'danger')

    return redirect(url_for('admin_panel'))


# -------------------------------------------------------------------
# 4. Easter Egg Route
# -------------------------------------------------------------------

@app.route('/fly')
def fly():
    """Easter egg: redirect to the Python antigravity XKCD comic."""
    return redirect('https://xkcd.com/353/')


# -------------------------------------------------------------------
# 5. Error Handlers
# -------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('layout.html', custom_message='404 - Page Not Found'), 404


# -------------------------------------------------------------------
# Initialization helper for direct execution
# -------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
