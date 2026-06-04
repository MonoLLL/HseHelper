from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from ..auth import create_token, decode_token, verify_password
from ..db import get_db
from ..faq_utils import faq_index_doc, faq_to_out
from ..models import AdminUser, FAQ, FAQAttachment, IncomingQuestion
from ..schemas import FAQCreate, FAQOut, IncomingStatus
from ..search_service import index_faq
from ..telegram_notify import send_staff_attachments, send_telegram_message
from ..time_utils import now_yekaterinburg
from .incoming import create_message, incoming_query, incoming_to_out


router = APIRouter()


def require_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Unauthorized")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")

    if payload.get("role") not in {"admin", "editor"}:
        raise HTTPException(403, "Forbidden")

    return payload


@router.post("/login")
def login(
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    db: Session = Depends(get_db),
):
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_token(user.email, user.role)}


@router.post("/faq", response_model=FAQOut)
def create_faq(payload: FAQCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = FAQ(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    index_faq(faq_index_doc(row))
    return faq_to_out(row)


@router.put("/faq/{faq_id}", response_model=FAQOut)
def update_faq(faq_id: UUID, payload: FAQCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not row:
        raise HTTPException(404, "FAQ not found")

    for key, value in payload.model_dump().items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    index_faq(faq_index_doc(row))
    return faq_to_out(row)


@router.post("/faq/{faq_id}/publish")
def publish_faq(faq_id: UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not row:
        raise HTTPException(404, "FAQ not found")
    row.status = "published"
    db.commit()
    db.refresh(row)
    index_faq(faq_index_doc(row))
    return {"ok": True}


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db), _=Depends(require_admin)):
    total = db.execute(text("select count(*) from faq_entries")).scalar() or 0
    published = db.execute(text("select count(*) from faq_entries where status='published'")).scalar() or 0
    return {"faq_total": total, "faq_published": published}


@router.get("/incoming")
def admin_list_incoming(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    items = incoming_query(db).order_by(IncomingQuestion.created_at.desc()).limit(200).all()
    return [incoming_to_out(item) for item in items]


@router.patch("/incoming/{incoming_id}")
async def update_incoming(
    incoming_id: str,
    status: Annotated[IncomingStatus, Form(...)],
    comment: str | None = Form(None),
    answer: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    old_status = item.status
    old_answer = item.answer

    item.status = status
    item.comment = comment
    item.answer = answer
    item.answered_at = now_yekaterinburg() if item.status == "done" else None

    try:
        if answer or files:
            create_message(db, item, "staff", answer, files)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()

    if item.telegram_user_id:
        if old_status != "in_progress" and item.status == "in_progress":
            send_telegram_message(item.telegram_user_id, "Ваше обращение взято в работу.")

        if item.status == "done" and item.answer and item.answer != old_answer:
            send_telegram_message(
                item.telegram_user_id,
                f"На ваше обращение поступил ответ:\n\n{item.answer}",
            )

    return incoming_to_out(item)


@router.post("/incoming/{incoming_id}/messages")
async def admin_send_message(
    incoming_id: str,
    text: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    publish_as_faq: bool = Form(False),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    try:
        message = create_message(db, item, "staff", text, files)
        db.flush()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if item.status == "new":
        item.status = "in_progress"

    if publish_as_faq and (text or "").strip():
        faq_text = (text or "").strip()
        faq_row = FAQ(
            question=item.text[:255],
            short_answer=faq_text[:400],
            full_answer=faq_text,
            status="published",
        )
        db.add(faq_row)
        db.flush()
        for attachment in message.attachments:
            db.add(
                FAQAttachment(
                    faq_id=faq_row.id,
                    original_name=attachment.original_name,
                    stored_path=attachment.stored_path,
                    mime_type=attachment.mime_type,
                    file_size=attachment.file_size,
                    created_at=attachment.created_at,
                )
            )
        index_faq(faq_index_doc(faq_row))

    db.commit()
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()

    if item.telegram_user_id:
        if text and text.strip():
            send_telegram_message(
                item.telegram_user_id,
                f"Новое сообщение от учебного офиса:\n\n{text.strip()}",
            )
        if message.attachments:
            send_telegram_message(item.telegram_user_id, "К сообщению прикреплены файлы:")
            send_staff_attachments(item.telegram_user_id, message.attachments)

    return incoming_to_out(item)


@router.get("/faq", response_model=list[FAQOut])
def list_faq(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    rows = db.query(FAQ).options(joinedload(FAQ.attachments)).order_by(FAQ.question.asc()).all()
    return [faq_to_out(row) for row in rows]
