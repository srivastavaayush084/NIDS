from backend.app.auth.roles import UserRole, ROLE_PERMISSIONS, has_permission
from backend.app.auth.password import hash_password, verify_password
from backend.app.auth.jwt import create_access_token, create_refresh_token, decode_token
from backend.app.auth.rate_limiter import login_rate_limiter
from backend.app.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserAuthInfo,
    CurrentUserResponse,
)
from backend.app.auth.dependencies import (
    get_current_user,
    require_authenticated_user,
    require_role,
    require_admin,
    require_analyst_or_admin,
    require_any_authenticated,
)

__all__ = [
    "UserRole",
    "ROLE_PERMISSIONS",
    "has_permission",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "login_rate_limiter",
    "LoginRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserAuthInfo",
    "CurrentUserResponse",
    "get_current_user",
    "require_authenticated_user",
    "require_role",
    "require_admin",
    "require_analyst_or_admin",
    "require_any_authenticated",
]
