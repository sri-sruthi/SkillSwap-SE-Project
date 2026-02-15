import os
import re
import sys
from typing import Optional

from app import models
from app.database import SessionLocal
from app.utils.security import get_password_hash


CONFIRM_PHRASE = "CREATE-FIRST-ADMIN"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EDU_RE = re.compile(r"^[^@\s]+@[^@\s]+\.edu$")


def _is_truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _required_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("ADMIN_PASSWORD must be <= 72 bytes (bcrypt limit).")
    if not re.search(r"[A-Z]", password):
        raise ValueError("ADMIN_PASSWORD must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("ADMIN_PASSWORD must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("ADMIN_PASSWORD must contain at least one digit.")


def bootstrap_admin() -> int:
    try:
        if not _is_truthy(os.getenv("ENABLE_ADMIN_BOOTSTRAP")):
            raise ValueError(
                "Bootstrap disabled. Set ENABLE_ADMIN_BOOTSTRAP=true to run."
            )
        confirm = _required_env("ADMIN_BOOTSTRAP_CONFIRM")
        if confirm != CONFIRM_PHRASE:
            raise ValueError(
                f"Invalid ADMIN_BOOTSTRAP_CONFIRM. Expected exact phrase: {CONFIRM_PHRASE}"
            )

        name = _required_env("ADMIN_NAME")
        email = _required_env("ADMIN_EMAIL").lower()
        password = _required_env("ADMIN_PASSWORD")
        enforce_edu = _is_truthy(os.getenv("ADMIN_ENFORCE_EDU", "true"))

        if not EMAIL_RE.match(email):
            raise ValueError("ADMIN_EMAIL is not a valid email format.")
        if enforce_edu and not EDU_RE.match(email):
            raise ValueError("ADMIN_EMAIL must be a .edu email when ADMIN_ENFORCE_EDU=true.")
        _validate_password(password)

        db = SessionLocal()
        try:
            existing_admin_count = db.query(models.User).filter(
                models.User.role == "admin"
            ).count()
            if existing_admin_count > 0:
                raise ValueError(
                    "Admin bootstrap blocked: an admin already exists. "
                    "This command is one-time for first admin creation."
                )

            existing_email = db.query(models.User).filter(
                models.User.email == email
            ).first()
            if existing_email:
                raise ValueError("ADMIN_EMAIL is already registered.")

            user = models.User(
                name=name,
                email=email,
                password_hash=get_password_hash(password),
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.flush()

            profile = models.UserProfile(
                user_id=user.id,
                full_name=name,
            )
            db.add(profile)

            wallet = models.TokenWallet(
                user_id=user.id,
                balance=20,
            )
            db.add(wallet)

            db.commit()
            print(f"Admin created successfully: {email}")
            return 0
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as exc:
        print(f"Admin bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(bootstrap_admin())
