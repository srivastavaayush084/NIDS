from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from backend.app.auth.roles import UserRole


class LoginRequest(BaseModel):
    """Payload for user authentication."""
    username: Optional[str] = Field(None, description="Username or email address")
    email: Optional[str] = Field(None, description="Email address (alternative to username)")
    password: str = Field(..., min_length=1, description="Plaintext password")


    def get_identifier(self) -> str:
        """Return provided username or email."""
        return (self.username or self.email or "").strip()


class RefreshTokenRequest(BaseModel):
    """Payload for token refresh."""
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class UserAuthInfo(BaseModel):
    """Safe user profile representation returned upon authentication."""
    id: str
    user_id: Optional[str] = None
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Authentication token response payload."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserAuthInfo


class CurrentUserResponse(BaseModel):
    """User profile response for /auth/me."""
    id: str
    user_id: Optional[str] = None
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
