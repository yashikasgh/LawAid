from typing import Literal

from pydantic import BaseModel, EmailStr, ConfigDict, Field

Role = Literal["citizen", "police", "lawyer", "admin"]

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role

class UserLoginRequest(BaseModel):
    """Login schema. User must provide the role of the portal they are logging in from."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: Role

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
