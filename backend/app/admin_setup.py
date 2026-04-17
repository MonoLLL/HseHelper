import os

from .auth import hash_password
from .db import SessionLocal
from .models import AdminUser


DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "").strip()
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Admin").strip() or "Admin"


def ensure_default_admin():
    if not DEFAULT_ADMIN_EMAIL or not DEFAULT_ADMIN_PASSWORD:
        return

    db = SessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.email == DEFAULT_ADMIN_EMAIL).first()
        if admin:
            return

        admin = AdminUser(
            email=DEFAULT_ADMIN_EMAIL,
            name=DEFAULT_ADMIN_NAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
