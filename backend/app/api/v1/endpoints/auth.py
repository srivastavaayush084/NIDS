from fastapi import APIRouter, Depends, Request, status
from backend.app.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    CurrentUserResponse,
)
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import UserDocument
from backend.app.services.auth_service import auth_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="User Authentication & Token Issuance")
async def login(request: Request, payload: LoginRequest) -> TokenResponse:
    """
    Authenticate user credentials (username or email + password).
    Returns signed access and refresh tokens with user authorization claims.
    """
    client_ip = request.client.host if request.client else "unknown"
    identifier = payload.get_identifier()
    return await auth_service.authenticate_user(
        identifier=identifier,
        password=payload.password,
        client_ip=client_ip,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh Access Token")
async def refresh_token(request: Request, payload: RefreshTokenRequest) -> TokenResponse:
    """
    Validate an active refresh token and issue a fresh access & refresh token pair.
    """
    client_ip = request.client.host if request.client else "unknown"
    return await auth_service.refresh_access_token(
        refresh_token=payload.refresh_token,
        client_ip=client_ip,
    )


@router.post("/logout", status_code=status.HTTP_200_OK, summary="User Logout")
async def logout(
    request: Request,
    current_user: UserDocument = Depends(get_current_user)
) -> dict:
    """
    Log out active user session and record security audit entry.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_id = current_user.user_id or current_user.id
    await auth_service.logout(user_id=user_id, client_ip=client_ip)
    return {"message": "Successfully logged out.", "status": "success"}


@router.get("/me", response_model=CurrentUserResponse, summary="Retrieve Current User Profile")
async def get_me(current_user: UserDocument = Depends(get_current_user)) -> CurrentUserResponse:
    """
    Return profile, permissions, and role designations for the authenticated user.
    """
    return CurrentUserResponse(
        id=current_user.id or "",
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )
