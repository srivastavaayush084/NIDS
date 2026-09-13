import re
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserDocument(BaseModel):
    """MongoDB document model for system users and analysts."""
    id: Optional[str] = Field(None, alias="_id")
    user_id: Optional[str] = Field(None, description="Explicit UUID / string identifier")
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    role: str = Field(default="analyst", description="admin, analyst, viewer")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        val = (v or "").strip().lower()
        if not val or not EMAIL_REGEX.match(val):
            raise ValueError(f"Invalid email address: '{v}'")
        return val

    model_config = ConfigDict(populate_by_name=True)

