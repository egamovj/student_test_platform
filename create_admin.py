from app import app, db, Admin

def create_admin(username, password):
    # Check if admin already exists
    admin = Admin.query.filter_by(username=username).first()
    if admin:
        print("Admin user already exists!")
        return
    
    # Create new admin
    admin = Admin(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print("Admin user created successfully!")

if __name__ == '__main__':
    with app.app_context():
        # Create the database tables
        db.create_all()
        
        # Create admin user
        create_admin('admin', 'admin123')
