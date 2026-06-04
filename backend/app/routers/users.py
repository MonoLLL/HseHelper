import re
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import create_token, decode_token, hash_password, verify_password
from ..db import get_db
from ..models import IncomingQuestion, StudentUser
from ..schemas import StudentUserOut
from ..time_utils import now_yekaterinburg


router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STUDENT_TOKEN_TTL_HOURS = 24 * 14


def clean_optional(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email")
    return email


def validate_password(value: str):
    if len(value) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")


def validate_profile(full_name: str, course: int | None, group_name: str | None):
    if len(full_name.strip()) < 3:
        raise HTTPException(status_code=400, detail="Full name is too short")

    if course is None or not 1 <= course <= 10:
        raise HTTPException(status_code=400, detail="Course must be between 1 and 10")

    if not clean_optional(group_name):
        raise HTTPException(status_code=400, detail="Group is required")


def build_student_token(user: StudentUser) -> str:
    return create_token(user.email, "student", expires_hours=STUDENT_TOKEN_TTL_HOURS)


def find_user(
    db: Session,
    client_id: str | None = None,
    telegram_user_id: str | None = None,
) -> StudentUser | None:
    filters = []
    if client_id:
        filters.append(StudentUser.client_id == client_id)
    if telegram_user_id:
        filters.append(StudentUser.telegram_user_id == telegram_user_id)

    if not filters:
        return None

    return db.query(StudentUser).filter(or_(*filters)).first()


def fill_profile(
    user: StudentUser,
    full_name: str,
    faculty: str | None,
    course: int | None,
    group_name: str | None,
):
    user.full_name = full_name.strip()
    user.faculty = clean_optional(faculty)
    user.course = course
    user.group_name = clean_optional(group_name)
    user.updated_at = now_yekaterinburg()


def fill_telegram_profile(
    user: StudentUser,
    telegram_user_id: str,
    telegram_username: str | None = None,
    telegram_first_name: str | None = None,
    telegram_last_name: str | None = None,
):
    user.telegram_user_id = telegram_user_id
    user.telegram_username = clean_optional(telegram_username)
    user.telegram_first_name = clean_optional(telegram_first_name)
    user.telegram_last_name = clean_optional(telegram_last_name)
    user.updated_at = now_yekaterinburg()


def merge_student_users(db: Session, target: StudentUser, source: StudentUser):
    if source.id == target.id:
        return target

    source_telegram_user_id = source.telegram_user_id

    if not target.faculty and source.faculty:
        target.faculty = source.faculty
    if target.course is None and source.course is not None:
        target.course = source.course
    if not target.group_name and source.group_name:
        target.group_name = source.group_name

    incoming_filters = [IncomingQuestion.student_user_id == source.id]
    if source_telegram_user_id:
        incoming_filters.append(IncomingQuestion.telegram_user_id == source_telegram_user_id)

    db.query(IncomingQuestion).filter(or_(*incoming_filters)).update(
        {IncomingQuestion.student_user_id: target.id},
        synchronize_session=False,
    )
    source.telegram_user_id = None
    source.telegram_username = None
    source.telegram_first_name = None
    source.telegram_last_name = None
    db.flush()
    db.delete(source)
    return target


def get_student_from_authorization(
    authorization: str | None,
    db: Session,
    required: bool = True,
) -> StudentUser | None:
    if not authorization or not authorization.startswith("Bearer "):
        if required:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return None

    try:
        payload = decode_token(token)
    except Exception:
        if required:
            raise HTTPException(status_code=401, detail="Invalid token")
        return None

    if payload.get("role") != "student":
        if required:
            raise HTTPException(status_code=403, detail="Forbidden")
        return None

    email = payload.get("sub")
    user = db.query(StudentUser).filter(StudentUser.email == email).first()
    if not user:
        if required:
            raise HTTPException(status_code=401, detail="Student account not found")
        return None

    return user


def require_student_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> StudentUser:
    return get_student_from_authorization(authorization, db, required=True)


@router.get("/users/telegram/{telegram_user_id}", response_model=StudentUserOut)
def get_user_by_telegram(
    telegram_user_id: str,
    db: Session = Depends(get_db),
):
    user = db.query(StudentUser).filter(StudentUser.telegram_user_id == telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User is not registered")
    return user


@router.post("/users/register", response_model=StudentUserOut)
def register_telegram_user(
    full_name: Annotated[str, Form(...)],
    telegram_user_id: Annotated[str, Form(...)],
    faculty: str | None = Form(None),
    course: int | None = Form(None),
    group_name: str | None = Form(None),
    telegram_username: str | None = Form(None),
    telegram_first_name: str | None = Form(None),
    telegram_last_name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    telegram_user_id = clean_optional(telegram_user_id)
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="Telegram user id is required")

    if len(full_name.strip()) < 3:
        raise HTTPException(status_code=400, detail="Full name is too short")

    if course is not None and not 1 <= course <= 10:
        raise HTTPException(status_code=400, detail="Course must be between 1 and 10")

    user = find_user(db, telegram_user_id=telegram_user_id)
    if user and user.email and user.password_hash:
        raise HTTPException(
            status_code=409,
            detail="Telegram is already linked to a site account",
        )

    if not user:
        user = StudentUser(
            telegram_user_id=telegram_user_id,
            full_name=full_name.strip(),
            created_at=now_yekaterinburg(),
        )
        db.add(user)

    user.telegram_user_id = telegram_user_id
    fill_telegram_profile(user, telegram_user_id, telegram_username, telegram_first_name, telegram_last_name)
    fill_profile(user, full_name, faculty, course, group_name)

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/telegram/login", response_model=StudentUserOut)
def login_telegram_with_site_account(
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    telegram_user_id: Annotated[str, Form(...)],
    telegram_username: str | None = Form(None),
    telegram_first_name: str | None = Form(None),
    telegram_last_name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    email = normalize_email(email)
    telegram_user_id = clean_optional(telegram_user_id)
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="Telegram user id is required")

    site_user = db.query(StudentUser).filter(StudentUser.email == email).first()
    if not site_user or not site_user.password_hash or not verify_password(password, site_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if site_user.telegram_user_id and site_user.telegram_user_id != telegram_user_id:
        raise HTTPException(status_code=409, detail="Email is already linked to another Telegram account")

    telegram_user = db.query(StudentUser).filter(StudentUser.telegram_user_id == telegram_user_id).first()
    if telegram_user and telegram_user.id != site_user.id:
        if telegram_user.email and telegram_user.email != site_user.email:
            raise HTTPException(status_code=409, detail="Telegram account is already linked to another email")
        merge_student_users(db, site_user, telegram_user)

    fill_telegram_profile(site_user, telegram_user_id, telegram_username, telegram_first_name, telegram_last_name)
    db.commit()
    db.refresh(site_user)
    return site_user


@router.post("/users/telegram/site-credentials", response_model=StudentUserOut)
def set_site_credentials_for_telegram_user(
    telegram_user_id: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    db: Session = Depends(get_db),
):
    telegram_user_id = clean_optional(telegram_user_id)
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="Telegram user id is required")

    email = normalize_email(email)
    validate_password(password)

    user = db.query(StudentUser).filter(StudentUser.telegram_user_id == telegram_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Telegram user is not registered")

    user_by_email = db.query(StudentUser).filter(StudentUser.email == email).first()
    if user_by_email and user_by_email.id != user.id:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user.email = email
    user.password_hash = hash_password(password)
    user.updated_at = now_yekaterinburg()

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/site/register")
def register_site_user(
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    full_name: Annotated[str, Form(...)],
    course: Annotated[int, Form(...)],
    group_name: Annotated[str, Form(...)],
    db: Session = Depends(get_db),
):
    email = normalize_email(email)
    full_name = full_name.strip()
    group_name = group_name.strip()

    validate_password(password)
    validate_profile(full_name, course, group_name)

    user_by_email = db.query(StudentUser).filter(StudentUser.email == email).first()
    if user_by_email:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = StudentUser(created_at=now_yekaterinburg())
    db.add(user)

    user.email = email
    user.client_id = None
    user.password_hash = hash_password(password)
    fill_profile(user, full_name, None, course, group_name)

    db.commit()
    db.refresh(user)

    return {"token": build_student_token(user), "user": user}


@router.post("/users/site/login")
def login_site_user(
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    db: Session = Depends(get_db),
):
    email = normalize_email(email)
    user = db.query(StudentUser).filter(StudentUser.email == email).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": build_student_token(user), "user": user}


@router.get("/users/site/me", response_model=StudentUserOut)
def get_current_site_user(user: StudentUser = Depends(require_student_user)):
    return user


@router.patch("/users/site/group", response_model=StudentUserOut)
def update_site_group(
    group_name: Annotated[str, Form(...)],
    user: StudentUser = Depends(require_student_user),
    db: Session = Depends(get_db),
):
    group_name = group_name.strip()
    if not group_name:
        raise HTTPException(status_code=400, detail="Group is required")

    user.group_name = group_name
    user.updated_at = now_yekaterinburg()
    db.commit()
    db.refresh(user)
    return user
