"""
Seed script to initialize and populate the recruitment database with test data:
- 2 Society Admins
- 2 Students
- 4 Societies (Tech & Cultural)
- Sample Applications (Accepted, Pending, Rejected)
"""

from app import app, db, User, Society, Application

def seed_database():
    with app.app_context():
        # Drop all tables and recreate them cleanly
        db.drop_all()
        db.create_all()
        print("[✓] Clean database tables created.")

        # 1. Create Admins
        tech_admin = User(
            name="Admin Taylor",
            email="tech_admin@college.edu",
            role="admin"
        )
        tech_admin.set_password("admin123")

        cultural_admin = User(
            name="Admin Jordan",
            email="cultural_admin@college.edu",
            role="admin"
        )
        cultural_admin.set_password("admin123")

        # 2. Create Students
        student1 = User(
            name="Morgan Lee",
            email="student@college.edu",
            role="student"
        )
        student1.set_password("password123")

        student2 = User(
            name="Sam Rivera",
            email="bob@college.edu",
            role="student"
        )
        student2.set_password("password123")

        db.session.add_all([tech_admin, cultural_admin, student1, student2])
        db.session.commit()
        print("[✓] Users (Admins and Students) seeded.")

        # 3. Create Societies
        gdsc = Society(
            name="Google Developer Student Club (GDSC)",
            description="Empowering student developers to bridge theory and real-world tech through Android, Cloud, AI/ML, and Web projects.",
            category="Tech",
            admin_id=tech_admin.id
        )

        cp_club = Society(
            name="Competitive Programming Society",
            description="Fostering algorithmic problem-solving skills, data structures mastery, and participating in ICPC and national hackathons.",
            category="Tech",
            admin_id=tech_admin.id
        )

        music_society = Society(
            name="Campus Symphony Club",
            description="The premier musical collective uniting vocalists, instrumentalists, and producers for campus concerts and state competitions.",
            category="Cultural",
            admin_id=cultural_admin.id
        )

        dramatics = Society(
            name="Thespian Dramatic Society",
            description="Celebrating theatrical excellence through street plays, stage dramas, scriptwriting workshops, and annual college fests.",
            category="Cultural",
            admin_id=cultural_admin.id
        )

        db.session.add_all([gdsc, cp_club, music_society, dramatics])
        db.session.commit()
        print("[✓] Societies seeded.")

        # 4. Create Initial Sample Applications
        app1 = Application(
            student_id=student1.id,
            society_id=gdsc.id,
            role_applied_for="Full-Stack Web Lead",
            status="Accepted"
        )

        app2 = Application(
            student_id=student1.id,
            society_id=music_society.id,
            role_applied_for="Keyboardist / Arranger",
            status="Pending"
        )

        app3 = Application(
            student_id=student2.id,
            society_id=gdsc.id,
            role_applied_for="Machine Learning Associate",
            status="Pending"
        )

        app4 = Application(
            student_id=student2.id,
            society_id=cp_club.id,
            role_applied_for="Contest Coordinator",
            status="Rejected"
        )

        db.session.add_all([app1, app2, app3, app4])
        db.session.commit()
        print("[✓] Sample applications seeded.")

        print("\n=======================================================")
        print("Database seeding completed successfully!")
        print("=======================================================")
        print("Demo Accounts:")
        print("1. Student User:")
        print("   Email:    student@college.edu")
        print("   Password: password123")
        print("2. Tech Society Admin:")
        print("   Email:    tech_admin@college.edu")
        print("   Password: admin123")
        print("3. Cultural Society Admin:")
        print("   Email:    cultural_admin@college.edu")
        print("   Password: admin123")
        print("=======================================================\n")

if __name__ == '__main__':
    seed_database()
