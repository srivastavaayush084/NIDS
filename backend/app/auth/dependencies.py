from typing import List, Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
from backend.app.auth.jwt import decode_token
from backend.app.auth.roles import UserRole
from backend.app.database.repository import UserRepository
from backend.app.models.user import UserDocument
from backend.app.services.audit_service import audit_service

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
    scheme_name="JWTBearer"
)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> UserDocument:
    """
    Extract and validate JWT Bearer token from request, resolving the authenticated UserDocument.
    """
    if not token:
        # Also check Authorization header directly if not captured by oauth2_scheme
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please refresh your token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository()
    user_dict = await user_repo.get_user_by_id(user_id)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_dict.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Format document
    doc_id = str(user_dict.get("_id") or user_dict.get("user_id"))
    user_doc = UserDocument(
        id=doc_id,
        user_id=str(user_dict.get("user_id") or doc_id),
        username=user_dict["username"],
        email=user_dict["email"],
        hashed_password=user_dict.get("hashed_password", ""),
        full_name=user_dict.get("full_name"),
        role=user_dict.get("role", "analyst").lower(),
        is_active=user_dict.get("is_active", True),
        created_at=user_dict.get("created_at"),
        updated_at=user_dict.get("updated_at"),
        last_login_at=user_dict.get("last_login_at"),
    )
    return user_doc


async def require_authenticated_user(
    current_user: UserDocument = Depends(get_current_user)
) -> UserDocument:
    """Dependency asserting that request has a valid active user session."""
    return current_user


def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Factory creating a FastAPI dependency to enforce RBAC permissions.
    """
    allowed_values = [r.value.lower() for r in allowed_roles]

    async def role_checker(
        request: Request,
        current_user: UserDocument = Depends(get_current_user),
    ) -> UserDocument:
        user_role = (current_user.role or "").lower()
        if user_role not in allowed_values:
            client_ip = request.client.host if request.client else "unknown"
            await audit_service.log_event(
                action="UNAUTHORIZED_ACCESS_ATTEMPT",
                resource=request.url.path,
                status="DENIED",
                user_id=current_user.user_id or current_user.id,
                ip_address=client_ip,
                metadata={
                    "user_role": user_role,
                    "required_roles": allowed_values,
                    "method": request.method,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required role in {[r.value.upper() for r in allowed_roles]}.",
            )
        return current_user

    return role_checker


# Convenient pre-configured role dependencies
require_admin = require_role(UserRole.ADMIN)
require_analyst_or_admin = require_role(UserRole.ADMIN, UserRole.ANALYST)
require_any_authenticated = require_role(UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER)
