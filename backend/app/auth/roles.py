from enum import Enum
from typing import Set


class UserRole(str, Enum):
    """Supported user role designations for Role-Based Access Control (RBAC)."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

    @classmethod
    def from_str(cls, value: str) -> "UserRole":
        """Safely parse case-insensitive role string."""
        val = (value or "").strip().lower()
        for role in cls:
            if role.value == val:
                return role
        raise ValueError(f"Invalid user role: '{value}'. Supported roles: {[r.value for r in cls]}")


# Role permission hierarchies
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        "dashboard:read",
        "monitoring:read",
        "monitoring:control",
        "detections:read",
        "detections:execute",
        "alerts:read",
        "alerts:triage",
        "models:read",
        "health:read",
        "users:read",
        "users:manage",
        "database:read",
    },
    UserRole.ANALYST: {
        "dashboard:read",
        "monitoring:read",
        "monitoring:control",
        "detections:read",
        "detections:execute",
        "alerts:read",
        "alerts:triage",
        "models:read",
        "health:read",
    },
    UserRole.VIEWER: {
        "dashboard:read",
        "monitoring:read",
        "detections:read",
        "alerts:read",
        "models:read",
        "health:read",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Check if the given role contains the requested permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
