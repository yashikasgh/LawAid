from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

class UserLoginRequest(BaseModel):
    """Login schema — role is intentionally excluded.
    The user's role is always loaded from the database, never trusted from client input."""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str