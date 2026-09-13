import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.repository import UserRepository
from backend.app.auth.password import verify_password, hash_password
from backend.app.auth.jwt import create_access_token, create_refresh_token, decode_token
from backend.app.auth.rate_limiter import login_rate_limiter
from backend.app.auth.schemas import TokenResponse, UserAuthInfo
from backend.app.services.audit_service import audit_service


class AuthService:
    """Core Authentication & Credential Verification Service."""

    def __init__(self, user_repo: Optional[UserRepository] = None):
        self._user_repo = user_repo

    @property
    def user_repo(self) -> UserRepository:
        if self._user_repo is None:
            self._user_repo = UserRepository()
        return self._user_repo

    async def authenticate_user(
        self,
        identifier: str,
        password: str,
        client_ip: Optional[str] = None,
    ) -> TokenResponse:
        """
        Authenticate user credentials, check rate limits, and issue JWT tokens.
        """
        clean_id = (identifier or "").strip()
        rate_key = f"{client_ip or 'unknown'}:{clean_id.lower()}"

        # 1. Rate Limit Check
        is_blocked, remaining_secs = login_rate_limiter.is_rate_limited(rate_key)
        if is_blocked:
            await audit_service.log_event(
                action="USER_LOGIN_BLOCKED",
                resource="auth",
                status="DENIED",
                ip_address=client_ip,
                metadata={"identifier": clean_id, "retry_after": remaining_secs},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Please try again in {remaining_secs} seconds.",
                headers={"Retry-After": str(remaining_secs)},
            )

        # 2. Database Lookup
        user = await self.user_repo.get_user_by_identifier(clean_id)
        if not user:
            login_rate_limiter.record_failure(rate_key)
            await audit_service.log_event(
                action="USER_LOGIN_FAILED",
                resource="auth",
                status="FAILURE",
                ip_address=client_ip,
                metadata={"identifier": clean_id, "reason": "user_not_found"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Account Active Status Check
        if not user.get("is_active", True):
            login_rate_limiter.record_failure(rate_key)
            user_id = str(user.get("user_id") or user.get("_id"))
            await audit_service.log_event(
                action="USER_LOGIN_FAILED",
                resource="auth",
                status="DENIED",
                user_id=user_id,
                ip_address=client_ip,
                metadata={"username": user.get("username"), "reason": "deactivated"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account has been deactivated. Please contact your system administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Password Verification
        stored_hash = user.get("hashed_password", "")
        if not verify_password(password, stored_hash):
            login_rate_limiter.record_failure(rate_key)
            user_id = str(user.get("user_id") or user.get("_id"))
            await audit_service.log_event(
                action="USER_LOGIN_FAILED",
                resource="auth",
                status="FAILURE",
                user_id=user_id,
                ip_address=client_ip,
                metadata={"username": user.get("username"), "reason": "invalid_password"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 5. Success Flow
        login_rate_limiter.record_success(rate_key)
        user_id_str = str(user.get("user_id") or user.get("_id"))
        username = user.get("username")
        role = user.get("role", "analyst").lower()

        now = datetime.now(timezone.utc)
        await self.user_repo.update_last_login(user_id_str, timestamp=now)

        claims = {
            "user_id": user_id_str,
            "username": username,
            "role": role,
            "email": user.get("email"),
        }

        access_token = create_access_token(subject=user_id_str, claims=claims)
        refresh_token = create_refresh_token(subject=user_id_str, claims=claims)

        await audit_service.log_event(
            action="USER_LOGIN",
            resource="auth",
            status="SUCCESS",
            user_id=user_id_str,
            ip_address=client_ip,
            metadata={"username": username, "role": role},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserAuthInfo(
                id=str(user.get("_id") or user_id_str),
                user_id=user_id_str,
                username=username,
                email=user.get("email", ""),
                full_name=user.get("full_name"),
                role=role,
                is_active=True,
                last_login_at=now,
            ),
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
        client_ip: Optional[str] = None,
    ) -> TokenResponse:
        """
        Validate JWT refresh token and issue new token pair.
        """
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except Exception as e:
            await audit_service.log_event(
                action="TOKEN_REFRESH_FAILED",
                resource="auth",
                status="FAILURE",
                ip_address=client_ip,
                metadata={"error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        user = await self.user_repo.get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            await audit_service.log_event(
                action="TOKEN_REFRESH_DENIED",
                resource="auth",
                status="DENIED",
                user_id=user_id,
                ip_address=client_ip,
                metadata={"reason": "user_not_found_or_inactive"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is no longer valid. User account not active.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = str(user.get("user_id") or user.get("_id"))
        role = user.get("role", "analyst").lower()
        username = user.get("username")

        claims = {
            "user_id": user_id_str,
            "username": username,
            "role": role,
            "email": user.get("email"),
        }

        new_access_token = create_access_token(subject=user_id_str, claims=claims)
        new_refresh_token = create_refresh_token(subject=user_id_str, claims=claims)

        await audit_service.log_event(
            action="TOKEN_REFRESH",
            resource="auth",
            status="SUCCESS",
            user_id=user_id_str,
            ip_address=client_ip,
            metadata={"username": username},
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserAuthInfo(
                id=str(user.get("_id") or user_id_str),
                user_id=user_id_str,
                username=username,
                email=user.get("email", ""),
                full_name=user.get("full_name"),
                role=role,
                is_active=True,
                last_login_at=user.get("last_login_at"),
            ),
        )

    async def logout(self, user_id: str, client_ip: Optional[str] = None) -> None:
        """Record user logout in audit log."""
        await audit_service.log_event(
            action="USER_LOGOUT",
            resource="auth",
            status="SUCCESS",
            user_id=user_id,
            ip_address=client_ip,
        )


auth_service = AuthService()
