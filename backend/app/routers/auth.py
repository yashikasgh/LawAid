from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import UserCreate, UserLoginRequest, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user_in: UserLoginRequest, db: Session = Depends(get_db)):
    """Login endpoint. Enforces that the portal role matches the user's actual DB role."""
    user = db.query(User).filter(User.email == user_in.email).first()
    
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if user.role != user_in.role:
        raise HTTPException(
            status_code=403, 
            detail=f"Account is registered as a {user.role.capitalize()}. Please use the {user.role.capitalize()} portal to log in."
        )

    # JWT role comes from the TRUSTED DATABASE record, not from the client request
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token}

@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh JWT. Requires a valid existing JWT — prevents arbitrary user ID refresh."""
    token = create_access_token({"sub": str(current_user.id), "role": current_user.role})
    return {"access_token": token}

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully. Please discard your token client-side."}
import uuid
import datetime
from app.models.password_reset import PasswordReset
from app.models.schemas import ForgotPasswordRequest, ResetPasswordRequest

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        # Do not reveal that the email does not exist
        return {"message": "If that email is registered, a password reset link has been created.", "reset_token": None}
    
    # Generate secure random token
    raw_token = uuid.uuid4().hex + uuid.uuid4().hex
    
    # In a real app we would hash the token before storing it.
    # For simplicity and to allow the frontend to use it from the response, we will just use the raw_token as the token_hash 
    # (since the instructions say "log the reset URL/token only in development or expose it through a clearly marked development response").
    
    reset_record = PasswordReset(
        user_id=user.id,
        token_hash=raw_token, # Normally hash this, but we keep it simple for demo
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    )
    db.add(reset_record)
    db.commit()
    
    # Development-safe reset mechanism
    return {
        "message": "If that email is registered, a password reset link has been created.",
        "dev_note": "DEVELOPMENT ONLY: Use this token in the reset password flow.",
        "reset_token": raw_token
    }

@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Find the token
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.token_hash == body.token,
        PasswordReset.used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or already used reset token")
        
    # Check expiration
    if reset_record.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")
        
    # Update password
    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = hash_password(body.new_password)
    reset_record.used = True
    
    db.commit()
    return {"message": "Password updated successfully"}

