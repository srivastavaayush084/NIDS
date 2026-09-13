#!/usr/bin/env python3
"""
ZeroDayAI - Development User Seeding Script.
Seeds one development user for each RBAC role (ADMIN, ANALYST, VIEWER) into MongoDB.
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

from backend.app.core.config import settings
from backend.app.database.connection import connect_to_mongo, close_mongo_connection, check_mongo_health
from backend.app.database.repository import UserRepository
from backend.app.auth.password import hash_password
from backend.app.services.audit_service import audit_service


SEEDED_ROLES = [
    {
        "role": "admin",
        "username": "admin",
        "email": "admin@zeroday.local",
        "full_name": "System Administrator",
        "default_pass": "Admin12345!",
    },
    {
        "role": "analyst",
        "username": "analyst",
        "email": "analyst@zeroday.local",
        "full_name": "Security Operations Analyst",
        "default_pass": "Analyst12345!",
    },
    {
        "role": "viewer",
        "username": "viewer",
        "email": "viewer@zeroday.local",
        "full_name": "Security Telemetry Viewer",
        "default_pass": "Viewer12345!",
    },
]


async def seed_users(
    admin_password: str = None,
    analyst_password: str = None,
    viewer_password: str = None,
    non_interactive: bool = False,
    update_passwords: bool = False,
) -> bool:

    print("=" * 60)
    print("ZERO-DAY NIDS - USER SEEDING")
    print("=" * 60)

    # 1. MongoDB Health & Ping Check
    print("[INFO] Verifying MongoDB database connectivity...")
    is_healthy, latency, details = await check_mongo_health()
    if not is_healthy:
        print("\n[ERROR] MongoDB connection failed.")
        print(f"[ERROR] Database: {settings.MONGODB_DATABASE}")
        print(f"[ERROR] Reason: {details.get('error', 'Unable to reach MongoDB instance')}")
        print("\nPlease ensure MongoDB is running and reachable before seeding users.")
        return False

    server_type = details.get("server_type", "Standalone")
    print(f"[OK] MongoDB connected successfully ({server_type}, ping: {latency} ms)")
    print(f"[OK] Target database: {settings.MONGODB_DATABASE}\n")

    # Connect connection pool
    await connect_to_mongo()
    repo = UserRepository()

    # Passwords map
    passwords = {
        "admin": admin_password,
        "analyst": analyst_password,
        "viewer": viewer_password,
    }

    results = []

    for item in SEEDED_ROLES:
        role_key = item["role"]
        username = item["username"]
        email = item["email"]
        full_name = item["full_name"]
        role_label = role_key.upper()

        # Check existing by username or email
        existing_user = await repo.get_user_by_username(username)
        if not existing_user:
            existing_user = await repo.get_user_by_email(email)

        if existing_user:
            existing_role = existing_user.get("role", "unknown").upper()
            user_id = str(existing_user.get("user_id") or existing_user.get("_id"))
            if update_passwords:
                pw = passwords.get(role_key) or (item["default_pass"] if non_interactive else None)
                if not pw:
                    pw = getpass.getpass(f"Enter new password for {role_label} ({username}): ").strip() or item["default_pass"]
                hashed_pwd = hash_password(pw)
                await repo.update_user(user_id, {"hashed_password": hashed_pwd, "is_active": True})
                print(f"[{role_label:7}] {email:26} -> Updated password successfully (role: {existing_role})")
                results.append((role_label, "UPDATED"))
            else:
                print(f"[{role_label:7}] {email:26} -> Already exists (role: {existing_role}, active: {existing_user.get('is_active', True)})")
                results.append((role_label, "ALREADY_EXISTS"))
            continue


        # Collect password securely if not provided
        pw = passwords.get(role_key)
        if not pw:
            if non_interactive:
                pw = item["default_pass"]
            else:
                pw = getpass.getpass(f"Enter password for {role_label} ({username}) [min 8 chars]: ").strip()
                if not pw:
                    pw = item["default_pass"]
                    print(f"  Using default development password for {role_label}")

        if len(pw) < 8:
            print(f"[ERROR] Password for {role_label} must be at least 8 characters.")
            await close_mongo_connection()
            return False

        user_id = f"usr-{role_key}-{uuid.uuid4().hex[:8]}"
        hashed_pwd = hash_password(pw)
        now = datetime.now(timezone.utc)

        user_doc = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "hashed_password": hashed_pwd,
            "full_name": full_name,
            "role": role_key,
            "is_active": True,
            "created_at": now,
            "updated_at": None,
            "last_login_at": None,
        }

        inserted_id = await repo.create_user(user_doc)
        await audit_service.log_event(
            action="USER_CREATED",
            resource="users",
            status="SUCCESS",
            user_id="system-seed",
            resource_id=user_id,
            metadata={"username": username, "email": email, "role": role_key, "source": "seed_script"},
        )

        print(f"[{role_label:7}] {email:26} -> Created successfully (ID: {user_id})")
        results.append((role_label, "CREATED"))

    # Summary table
    print("\n" + "=" * 60)
    print("USER SEEDING SUMMARY")
    print("=" * 60)

    admin_count = await repo.count({"role": "admin", "is_active": True})
    analyst_count = await repo.count({"role": "analyst", "is_active": True})
    viewer_count = await repo.count({"role": "viewer", "is_active": True})

    print(f"  ADMIN    -> {admin_count} active user(s)")
    print(f"  ANALYST  -> {analyst_count} active user(s)")
    print(f"  VIEWER   -> {viewer_count} active user(s)")
    print("=" * 60)
    print("User seeding completed successfully.\n")

    await close_mongo_connection()
    return True


def main():
    parser = argparse.ArgumentParser(description="Seed development users for all RBAC roles.")
    parser.add_argument("--admin-pass", dest="admin_pass", help="Password for ADMIN account")
    parser.add_argument("--analyst-pass", dest="analyst_pass", help="Password for ANALYST account")
    parser.add_argument("--viewer-pass", dest="viewer_pass", help="Password for VIEWER account")
    parser.add_argument("--non-interactive", action="store_true", help="Run non-interactively using default development credentials")
    parser.add_argument("--update-passwords", action="store_true", help="Update passwords for already existing users")

    args = parser.parse_args()

    success = asyncio.run(
        seed_users(
            admin_password=args.admin_pass,
            analyst_password=args.analyst_pass,
            viewer_password=args.viewer_pass,
            non_interactive=args.non_interactive,
            update_passwords=args.update_passwords,
        )
    )


    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
