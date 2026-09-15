import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.core.security import hash_password
def seed_db():
    print("Running database seed...")
    try:
        db: Session = SessionLocal()
        users_to_seed = [
            {"email": "citizen@lawaid.com", "password": "password123", "role": "citizen"},
            {"email": "police@lawaid.com", "password": "password123", "role": "police"},
            {"email": "lawyer@lawaid.com", "password": "password123", "role": "lawyer"}
        ]
        for u in users_to_seed:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                new_user = User(email=u["email"], password_hash=hash_password(u["password"]), role=u["role"])
                db.add(new_user)
                print(f"Seeded user: {u[
'
email
'
]}")
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error during seeding: {e}")
if __name__ == "__main__":
    seed_db()
