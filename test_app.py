import unittest
from app import app, db, User, Society, Application
from werkzeug.security import check_password_hash

class RecruitmentWebsiteTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing with an in-memory SQLite database
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Create test admin
            self.admin = User(name='Admin User', email='admin@test.edu', role='admin')
            self.admin.set_password('adminpass')

            # Create another admin
            self.other_admin = User(name='Other Admin', email='other_admin@test.edu', role='admin')
            self.other_admin.set_password('adminpass')

            # Create test student
            self.student = User(name='Student User', email='student@test.edu', role='student')
            self.student.set_password('studentpass')

            db.session.add_all([self.admin, self.other_admin, self.student])
            db.session.commit()

            # Create societies
            self.society = Society(
                name='GDSC Club',
                description='Google Developer Student Club',
                category='Tech',
                admin_id=self.admin.id
            )
            self.other_society = Society(
                name='Arts Club',
                description='Campus Fine Arts Society',
                category='Arts',
                admin_id=self.other_admin.id
            )
            db.session.add_all([self.society, self.other_society])
            db.session.commit()

            # Keep IDs
            self.admin_id = self.admin.id
            self.student_id = self.student.id
            self.society_id = self.society.id
            self.other_society_id = self.other_society.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # -------------------------------------------------------------
    # 1. Database & Security Tests
    # -------------------------------------------------------------
    def test_password_hashing(self):
        """Verify that passwords are never stored in plaintext."""
        with self.app.app_context():
            user = User.query.filter_by(email='student@test.edu').first()
            self.assertNotEqual(user.password_hash, 'studentpass')
            self.assertTrue(user.password_hash.startswith(('scrypt:', 'pbkdf2:')))
            self.assertTrue(user.check_password('studentpass'))
            self.assertFalse(user.check_password('wrongpass'))

    # -------------------------------------------------------------
    # 2. Authentication Flow Tests
    # -------------------------------------------------------------
    def test_user_registration(self):
        """Test registration flow for a new student."""
        response = self.client.post('/register', data={
            'name': 'New Student',
            'email': 'newstudent@test.edu',
            'password': 'mypassword',
            'role': 'student'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            new_user = User.query.filter_by(email='newstudent@test.edu').first()
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.role, 'student')
            self.assertTrue(new_user.check_password('mypassword'))

    def test_login_and_logout(self):
        """Test user login and session clearing on logout."""
        # Valid login
        login_res = self.client.post('/login', data={
            'email': 'student@test.edu',
            'password': 'studentpass'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Student Dashboard', login_res.data)

        # Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'logged out', logout_res.data)

    # -------------------------------------------------------------
    # 3. Role-Based Access Control (RBAC) & 403 Forbidden Tests
    # -------------------------------------------------------------
    def test_admin_route_unauthenticated_redirects(self):
        """Unauthenticated user accessing /admin should be redirected to login."""
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_admin_route_student_forbidden_403(self):
        """Normal student accessing /admin MUST receive HTTP 403 Forbidden."""
        # Log in as student
        self.client.post('/login', data={
            'email': 'student@test.edu',
            'password': 'studentpass'
        })

        # Attempt to access /admin
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'403 - Access Forbidden', response.data)

    def test_admin_route_admin_allowed_200(self):
        """Admin user accessing /admin should succeed with HTTP 200 OK."""
        # Log in as admin
        self.client.post('/login', data={
            'email': 'admin@test.edu',
            'password': 'adminpass'
        })

        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Society Admin Panel', response.data)

    # -------------------------------------------------------------
    # 4. Recruitment Application Workflow Tests
    # -------------------------------------------------------------
    def test_student_can_apply_to_society(self):
        """Student can submit an application for an open role in a society."""
        self.client.post('/login', data={
            'email': 'student@test.edu',
            'password': 'studentpass'
        })

        response = self.client.post(f'/apply/{self.society_id}', data={
            'role_applied_for': 'Lead Mobile Developer'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lead Mobile Developer', response.data)

        with self.app.app_context():
            application = Application.query.filter_by(
                student_id=self.student_id,
                society_id=self.society_id
            ).first()
            self.assertIsNotNone(application)
            self.assertEqual(application.role_applied_for, 'Lead Mobile Developer')
            self.assertEqual(application.status, 'Pending')

    def test_admin_can_update_application_status(self):
        """Admin can accept or reject an application for their society."""
        # Create an application
        with self.app.app_context():
            app_entry = Application(
                student_id=self.student_id,
                society_id=self.society_id,
                role_applied_for='DevOps Lead',
                status='Pending'
            )
            db.session.add(app_entry)
            db.session.commit()
            app_id = app_entry.id

        # Log in as admin
        self.client.post('/login', data={
            'email': 'admin@test.edu',
            'password': 'adminpass'
        })

        # Update status to Accepted
        response = self.client.post(f'/admin/update_status/{app_id}', data={
            'status': 'Accepted'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            updated_app = db.session.get(Application, app_id)
            self.assertEqual(updated_app.status, 'Accepted')

    def test_admin_cannot_update_other_society_application(self):
        """Admin cannot update an application that belongs to a society they do not manage (RBAC 403)."""
        # Create an application for other_society
        with self.app.app_context():
            app_entry = Application(
                student_id=self.student_id,
                society_id=self.other_society_id,
                role_applied_for='Painter',
                status='Pending'
            )
            db.session.add(app_entry)
            db.session.commit()
            app_id = app_entry.id

        # Log in as admin (who manages GDSC, NOT Arts Club)
        self.client.post('/login', data={
            'email': 'admin@test.edu',
            'password': 'adminpass'
        })

        # Attempt to update the status of an application for other_society
        response = self.client.post(f'/admin/update_status/{app_id}', data={
            'status': 'Accepted'
        })
        self.assertEqual(response.status_code, 403)

    # -------------------------------------------------------------
    # 5. Easter Egg Test
    # -------------------------------------------------------------
    def test_easter_egg_fly_redirect(self):
        """GET /fly must redirect to the Python antigravity XKCD comic."""
        response = self.client.get('/fly')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'https://xkcd.com/353/')

if __name__ == '__main__':
    unittest.main()

