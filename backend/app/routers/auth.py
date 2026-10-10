import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.models.schemas import UserCreate, UserLoginRequest, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalized_email(email: str) -> str:
    return email.strip().lower()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.JWT_EXPIRY_HOURS * 60 * 60,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.role != "citizen":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Police and Lawyer accounts must be provisioned by an authorized administrator.",
        )

    email = _normalized_email(str(user_in.email))
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user_in: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login endpoint. Enforces that the portal role matches the user's actual DB role."""
    email = _normalized_email(str(user_in.email))
    user = db.query(User).filter(func.lower(User.email) == email).first()
    
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if user.role != user_in.role:
        raise HTTPException(
            status_code=403, 
            detail=f"Account is registered as a {user.role.capitalize()}. Please use the {user.role.capitalize()} portal to log in."
        )

    # JWT role comes from the TRUSTED DATABASE record, not from the client request
    token = create_access_token({"sub": str(user.id), "role": user.role})
    _set_session_cookie(response, token)
    return {"access_token": token}

@router.post("/refresh", response_model=Token)
def refresh_token(response: Response, current_user: User = Depends(get_current_user)):
    """Refresh JWT. Requires a valid existing JWT — prevents arbitrary user ID refresh."""
    token = create_access_token({"sub": str(current_user.id), "role": current_user.role})
    _set_session_cookie(response, token)
    return {"access_token": token}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out successfully."}

from app.models.password_reset import PasswordReset
from app.models.schemas import ForgotPasswordRequest, ResetPasswordRequest

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = _normalized_email(str(body.email))
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        # Do not reveal that the email does not exist
        return {"message": "If that email is registered, password reset instructions will be sent."}
    
    # Generate secure random token
    raw_token = secrets.token_urlsafe(48)
    reset_record = PasswordReset(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset_record)
    db.commit()
    
    # Delivery is delegated to deployment email infrastructure. Raw reset
    # tokens and account existence are never exposed in an API response.
    return {"message": "If that email is registered, password reset instructions will be sent."}

@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.token_hash == token_hash,
        PasswordReset.used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or already used reset token")
        
    # Check expiration
    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")
        
    # Update password
    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = hash_password(body.new_password)
    reset_record.used = True
    
    db.commit()
    return {"message": "Password updated successfully"}

