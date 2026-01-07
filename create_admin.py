from sqlalchemy.orm import Session
from backend import models, database, auth

def create_admin_user():
    db = database.SessionLocal()
    
    email = "admin@nyaya.com"
    password = "admin123"
    
    # Check if exists
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        print(f"User {email} already exists.")
        return

    # Create Admin
    hashed_password = auth.get_password_hash(password)
    admin_user = models.User(
        email=email,
        full_name="System Administrator",
        hashed_password=hashed_password,
        role="admin",
        preferred_language="en"
    )
    
    db.add(admin_user)
    db.commit()
    print(f"✅ Admin User Created successfully.")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print("Login at: http://127.0.0.1:8000/login")

if __name__ == "__main__":
    create_admin_user()
