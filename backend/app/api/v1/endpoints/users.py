import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from backend.app.auth.dependencies import require_admin, get_current_user
from backend.app.auth.password import hash_password
from backend.app.database.repository import UserRepository
from backend.app.models.user import UserDocument
from backend.app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from backend.app.services.audit_service import audit_service

router = APIRouter()


@router.get("", response_model=UserListResponse, summary="List System Users (Admin Only)")
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    role: Optional[str] = Query(None, description="Filter by role (admin, analyst, viewer)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: UserDocument = Depends(require_admin),
) -> UserListResponse:
    """
    Retrieve paginated user directory. Requires administrator role.
    """
    repo = UserRepository()
    users_raw = await repo.list_users(limit=limit, skip=skip, role=role, is_active=is_active)
    total = await repo.count({"role": role.lower()} if role else {})

    user_responses = []
    for u in users_raw:
        doc_id = str(u.get("_id") or u.get("user_id"))
        user_responses.append(
            UserResponse(
                id=doc_id,
                user_id=str(u.get("user_id") or doc_id),
                username=u["username"],
                email=u["email"],
                full_name=u.get("full_name"),
                role=u.get("role", "analyst").lower(),
                is_active=u.get("is_active", True),
                created_at=u.get("created_at") or datetime.now(timezone.utc),
                updated_at=u.get("updated_at"),
                last_login_at=u.get("last_login_at"),
            )
        )

    return UserListResponse(total=total, users=user_responses)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create New User (Admin Only)")
async def create_user(
    request: Request,
    payload: UserCreate,
    current_user: UserDocument = Depends(require_admin),
) -> UserResponse:
    """
    Create a new system user account. Requires administrator role.
    """
    repo = UserRepository()
    clean_username = payload.username.strip()
    clean_email = payload.email.strip().lower()

    # Verify unique username
    existing_user = await repo.get_user_by_username(clean_username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{clean_username}' is already in use.",
        )

    # Verify unique email
    existing_email = await repo.get_user_by_email(clean_email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email address '{clean_email}' is already registered.",
        )

    user_id = f"usr-{uuid.uuid4().hex[:12]}"
    hashed_pwd = hash_password(payload.password)
    now = datetime.now(timezone.utc)

    user_doc = {
        "user_id": user_id,
        "username": clean_username,
        "email": clean_email,
        "hashed_password": hashed_pwd,
        "full_name": payload.full_name,
        "role": payload.role.lower(),
        "is_active": payload.is_active,
        "created_at": now,
        "updated_at": None,
        "last_login_at": None,
    }

    inserted_id = await repo.create_user(user_doc)
    client_ip = request.client.host if request.client else "unknown"
    await audit_service.log_event(
        action="USER_CREATED",
        resource="users",
        status="SUCCESS",
        user_id=current_user.user_id or current_user.id,
        resource_id=user_id,
        ip_address=client_ip,
        metadata={"created_username": clean_username, "created_role": payload.role.lower()},
    )

    return UserResponse(
        id=str(inserted_id or user_id),
        user_id=user_id,
        username=clean_username,
        email=clean_email,
        full_name=payload.full_name,
        role=payload.role.lower(),
        is_active=payload.is_active,
        created_at=now,
        updated_at=None,
        last_login_at=None,
    )


@router.get("/{user_id}", response_model=UserResponse, summary="Retrieve User By ID")
async def get_user_by_id(
    user_id: str,
    current_user: UserDocument = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve single user profile. Administrators can view any user; other users can view their own profile.
    """
    is_admin = (current_user.role or "").lower() == "admin"
    is_self = current_user.user_id == user_id or current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You may only view your own user profile.",
        )

    repo = UserRepository()
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    doc_id = str(user.get("_id") or user.get("user_id"))
    return UserResponse(
        id=doc_id,
        user_id=str(user.get("user_id") or doc_id),
        username=user["username"],
        email=user["email"],
        full_name=user.get("full_name"),
        role=user.get("role", "analyst").lower(),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at") or datetime.now(timezone.utc),
        updated_at=user.get("updated_at"),
        last_login_at=user.get("last_login_at"),
    )


@router.patch("/{user_id}", response_model=UserResponse, summary="Update User Details (Admin Only)")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    current_user: UserDocument = Depends(require_admin),
) -> UserResponse:
    """
    Update user email, full name, role, active status, or password. Requires administrator role.
    Prevents deactivating the final active administrator account.
    """
    repo = UserRepository()
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    update_fields = {}
    if payload.email is not None:
        clean_email = payload.email.strip().lower()
        if clean_email != user.get("email"):
            existing = await repo.get_user_by_email(clean_email)
            if existing and str(existing.get("_id")) != str(user.get("_id")):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email address '{clean_email}' is already in use by another user.",
                )
        update_fields["email"] = clean_email

    if payload.full_name is not None:
        update_fields["full_name"] = payload.full_name

    # Check admin safety if role changed or deactivated
    target_is_admin = user.get("role", "").lower() == "admin"
    if (payload.role is not None and payload.role.lower() != "admin" and target_is_admin) or (
        payload.is_active is False and target_is_admin and user.get("is_active", True)
    ):
        active_admins = await repo.count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operation rejected: Cannot demote or deactivate the last remaining active administrator.",
            )

    if payload.role is not None:
        update_fields["role"] = payload.role.lower()

    if payload.is_active is not None:
        update_fields["is_active"] = payload.is_active

    if payload.password is not None:
        update_fields["hashed_password"] = hash_password(payload.password)

    if update_fields:
        await repo.update_user(user_id, update_fields)
        client_ip = request.client.host if request.client else "unknown"
        await audit_service.log_event(
            action="USER_UPDATED",
            resource="users",
            status="SUCCESS",
            user_id=current_user.user_id or current_user.id,
            resource_id=user_id,
            ip_address=client_ip,
            metadata={"updated_fields": list(update_fields.keys())},
        )

    # Fetch fresh user
    updated_user = await repo.get_user_by_id(user_id)
    doc_id = str(updated_user.get("_id") or updated_user.get("user_id"))
    return UserResponse(
        id=doc_id,
        user_id=str(updated_user.get("user_id") or doc_id),
        username=updated_user["username"],
        email=updated_user["email"],
        full_name=updated_user.get("full_name"),
        role=updated_user.get("role", "analyst").lower(),
        is_active=updated_user.get("is_active", True),
        created_at=updated_user.get("created_at") or datetime.now(timezone.utc),
        updated_at=updated_user.get("updated_at"),
        last_login_at=updated_user.get("last_login_at"),
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Deactivate User (Admin Only)")
async def deactivate_user(
    user_id: str,
    request: Request,
    current_user: UserDocument = Depends(require_admin),
) -> dict:
    """
    Deactivate user account. Requires administrator role.
    Prevents deactivating the final active administrator account.
    """
    repo = UserRepository()
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    if user.get("role", "").lower() == "admin" and user.get("is_active", True):
        active_admins = await repo.count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operation rejected: Cannot deactivate the last remaining active administrator.",
            )

    await repo.deactivate_user(user_id)
    client_ip = request.client.host if request.client else "unknown"
    await audit_service.log_event(
        action="USER_DEACTIVATED",
        resource="users",
        status="SUCCESS",
        user_id=current_user.user_id or current_user.id,
        resource_id=user_id,
        ip_address=client_ip,
        metadata={"username": user.get("username")},
    )

    return {"message": f"User '{user.get('username')}' has been deactivated.", "status": "success"}
