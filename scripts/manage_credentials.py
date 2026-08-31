#!/usr/bin/env python3
"""
Lentis Event Gallery — Credential Management Script
====================================================

Usage (inside the backend container):
    docker exec -it gall-backend-1 python /scripts/manage_credentials.py \
        --action reset-admin \
        --email admin@lentisevent.gallery \
        --password "YourNewPassword123"

    docker exec -it gall-backend-1 python /scripts/manage_credentials.py \
        --action create-user \
        --email host@example.com \
        --password "HostPassword123" \
        --role HOST

    docker exec -it gall-backend-1 python /scripts/manage_credentials.py \
        --action list-users

    docker exec -it gall-backend-1 python /scripts/manage_credentials.py \
        --action verify-login \
        --email admin@lentisevent.gallery \
        --password "YourNewPassword123"

Security:
    - Passwords are NEVER printed after hashing.
    - Script must be run on the server, not remotely.
    - No passwords are logged or stored in files.
"""

import argparse
import os
import sys

# Ensure we can import from the backend app
# Try multiple paths: mounted at /scripts in Docker, or local development
_backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if os.path.isdir(os.path.join(_backend_path, "app")):
    sys.path.insert(0, _backend_path)
else:
    # Running inside Docker — /app is the backend
    sys.path.insert(0, "/app")

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.core.security import hash_password, verify_password, validate_password_strength


def get_db_session():
    """Create a database session using the same DATABASE_URL as the backend."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set. This script must run inside the backend container.")
        sys.exit(1)
    engine = create_engine(db_url)
    return Session(engine)


def list_users(session: Session):
    """List all users (without exposing password hashes)."""
    users = session.scalars(select(User)).all()
    print(f"\n{'ID':<38} {'Email':<35} {'Role':<8} {'Active':<8} {'Last Login'}")
    print("-" * 120)
    for u in users:
        last_login = u.last_login_at.strftime("%Y-%m-%d %H:%M UTC") if u.last_login_at else "Never"
        print(f"{u.id:<38} {u.email:<35} {u.role.value:<8} {str(u.is_active):<8} {last_login}")
    print(f"\nTotal: {len(users)} users")


def reset_admin(session: Session, email: str, password: str):
    """Reset (or create) the admin account with the given email and password."""
    # Validate password strength
    strength_error = validate_password_strength(password)
    if strength_error:
        print(f"ERROR: {strength_error}")
        sys.exit(1)

    normalized_email = email.strip().lower()
    password_hash = hash_password(password)

    # Check if an admin already exists
    admin = session.scalar(select(User).where(User.role == UserRole.ADMIN))

    if admin:
        old_email = admin.email
        admin.email = normalized_email
        admin.password_hash = password_hash
        admin.is_active = True
        session.commit()
        print(f"\n✓ Admin account UPDATED:")
        print(f"  Old email:  {old_email}")
        print(f"  New email:  {normalized_email}")
        print(f"  Role:       ADMIN")
        print(f"  Active:     True")
    else:
        user = User(
            email=normalized_email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"\n✓ Admin account CREATED:")
        print(f"  ID:    {user.id}")
        print(f"  Email: {normalized_email}")
        print(f"  Role:  ADMIN")


def create_user(session: Session, email: str, password: str, role_str: str):
    """Create a new user with the given role."""
    strength_error = validate_password_strength(password)
    if strength_error:
        print(f"ERROR: {strength_error}")
        sys.exit(1)

    normalized_email = email.strip().lower()

    # Check for duplicate
    existing = session.scalar(select(User).where(User.email == normalized_email))
    if existing:
        print(f"ERROR: A user with email '{normalized_email}' already exists (id={existing.id}).")
        sys.exit(1)

    try:
        role = UserRole(role_str.upper())
    except ValueError:
        print(f"ERROR: Invalid role '{role_str}'. Must be ADMIN or HOST.")
        sys.exit(1)

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"\n✓ User CREATED:")
    print(f"  ID:    {user.id}")
    print(f"  Email: {normalized_email}")
    print(f"  Role:  {role.value}")


def verify_login(session: Session, email: str, password: str):
    """Verify that a login would succeed (without issuing tokens)."""
    normalized_email = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized_email))

    if not user:
        print(f"\n✗ No user found with email: {normalized_email}")
        sys.exit(1)

    if not user.is_active:
        print(f"\n✗ User is inactive: {normalized_email}")
        sys.exit(1)

    if not verify_password(password, user.password_hash):
        print(f"\n✗ Password is INCORRECT for: {normalized_email}")
        sys.exit(1)

    print(f"\n✓ Login verification PASSED:")
    print(f"  Email:  {normalized_email}")
    print(f"  Role:   {user.role.value}")
    print(f"  Active: {user.is_active}")


def main():
    parser = argparse.ArgumentParser(description="Lentis credential management")
    parser.add_argument(
        "--action",
        choices=["list-users", "reset-admin", "create-user", "verify-login"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--email", help="User email")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--role", default="HOST", help="User role (ADMIN or HOST)")

    args = parser.parse_args()

    session = get_db_session()
    try:
        if args.action == "list-users":
            list_users(session)

        elif args.action == "reset-admin":
            if not args.email or not args.password:
                print("ERROR: --email and --password are required for reset-admin.")
                sys.exit(1)
            reset_admin(session, args.email, args.password)

        elif args.action == "create-user":
            if not args.email or not args.password:
                print("ERROR: --email and --password are required for create-user.")
                sys.exit(1)
            create_user(session, args.email, args.password, args.role)

        elif args.action == "verify-login":
            if not args.email or not args.password:
                print("ERROR: --email and --password are required for verify-login.")
                sys.exit(1)
            verify_login(session, args.email, args.password)

    finally:
        session.close()


if __name__ == "__main__":
    main()
