#!/usr/bin/env python3
"""
Controlled Administrator Initialization CLI Utility.
Safely initializes the primary administrator account for the ZeroDayAI platform.
Must be executed using backend/.venv.
"""
import asyncio
import argparse
import getpass
import os
import sys
import uuid
from datetime import datetime, timezone

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.connection import connect_to_mongo, close_mongo_connection
from backend.app.database.repository import UserRepository
from backend.app.auth.password import hash_password
from backend.app.services.audit_service import audit_service


async def init_admin(
    username: str,
    email: str,
    password: str,
    full_name: str = "System Administrator",
    force: bool = False,
) -> bool:
    print("=" * 60)
    print("ZeroDayAI - Administrator Account Provisioning")
    print("=" * 60)

    connected = await connect_to_mongo()
    if not connected:
        print("[ERROR] Could not establish MongoDB connection. Please verify database is running.")
        return False

    repo = UserRepository()

    # Check existing admins
    active_admins = await repo.count_active_admins()
    if active_admins > 0 and not force:
        print(f"[INFO] System already has {active_admins} active administrator(s).")
        print("[INFO] Initialization aborted. Use the administrative API or --force flag if needed.")
        await close_mongo_connection()
        return False

    clean_username = username.strip()
    clean_email = email.strip().lower()

    # Check for username / email conflict
    if await repo.get_user_by_username(clean_username):
        print(f"[ERROR] User with username '{clean_username}' already exists.")
        await close_mongo_connection()
        return False

    if await repo.get_user_by_email(clean_email):
        print(f"[ERROR] User with email '{clean_email}' already exists.")
        await close_mongo_connection()
        return False

    user_id = f"usr-admin-{uuid.uuid4().hex[:8]}"
    hashed_pwd = hash_password(password)
    now = datetime.now(timezone.utc)

    user_doc = {
        "user_id": user_id,
        "username": clean_username,
        "email": clean_email,
        "hashed_password": hashed_pwd,
        "full_name": full_name,
        "role": "admin",
        "is_active": True,
        "created_at": now,
        "updated_at": None,
        "last_login_at": None,
    }

    inserted_id = await repo.create_user(user_doc)
    await audit_service.log_event(
        action="ADMIN_INITIALIZATION",
        resource="users",
        status="SUCCESS",
        user_id=user_id,
        resource_id=user_id,
        metadata={"username": clean_username, "email": clean_email},
    )

    print(f"[SUCCESS] Administrator '{clean_username}' provisioned successfully!")
    print(f"  User ID : {user_id}")
    print(f"  Email   : {clean_email}")
    print(f"  Role    : ADMIN")
    print("=" * 60)

    await close_mongo_connection()
    return True


def main():
    parser = argparse.ArgumentParser(description="Initialize the primary platform administrator account.")
    parser.add_argument("--username", help="Administrator username")
    parser.add_argument("--email", help="Administrator email address")
    parser.add_argument("--password", help="Administrator password")
    parser.add_argument("--name", default="System Administrator", help="Administrator full name")
    parser.add_argument("--force", action="store_true", help="Force creation even if administrators exist")

    args = parser.parse_args()

    username = args.username
    if not username:
        username = input("Enter Administrator username [admin]: ").strip() or "admin"

    email = args.email
    if not email:
        email = input(f"Enter Administrator email [{username}@zeroday.ai]: ").strip() or f"{username}@zeroday.ai"

    password = args.password
    if not password:
        password = getpass.getpass("Enter Administrator password (min 8 chars): ")
        password_confirm = getpass.getpass("Confirm Administrator password: ")
        if password != password_confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    success = asyncio.run(init_admin(
        username=username,
        email=email,
        password=password,
        full_name=args.name,
        force=args.force,
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
