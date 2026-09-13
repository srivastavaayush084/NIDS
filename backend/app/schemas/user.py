import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from backend.app.auth.roles import UserRole

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_str(v: str) -> str:
    val = (v or "").strip().lower()
    if not val or not EMAIL_REGEX.match(val):
        raise ValueError(f"Invalid email address: '{v}'. Must be formatted like user@domain.com or user@zeroday.local")
    return val


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    full_name: Optional[str] = None
    role: str = Field(default="analyst")
    is_active: bool = True

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return validate_email_str(v)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if v is None:
            return "analyst"
        val = str(v).strip().lower()
        if val not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {[r.value for r in UserRole]}")
        return val


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Minimum 8 characters password")


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_email_str(v)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        val = str(v).strip().lower()
        if val not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {[r.value for r in UserRole]}")
        return val



class UserResponse(UserBase):
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    total: int
    users: List[UserResponse]

