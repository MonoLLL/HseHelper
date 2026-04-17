from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.file_storage import save_upload_file

from ..auth import create_token, decode_token, verify_password
from ..db import get_db
from ..models import AdminUser, FAQ, IncomingQuestion, IncomingQuestionAttachment
from ..schemas import FAQCreate, FAQOut, IncomingStatus
from ..search_service import index_faq
from ..telegram_notify import send_staff_attachments, send_telegram_message
from .incoming import incoming_to_out


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
    user = db.query(AdminUser).filter(AdminUser.email==email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_token(user.email, user.role)}

@router.post("/faq", response_model=FAQOut)
def create_faq(payload: FAQCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = FAQ(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    index_faq({
        "id": str(row.id), "question": row.question, "short_answer": row.short_answer,
        "full_answer": row.full_answer, "tags": row.tags or [], "synonyms": row.synonyms or [],
        "faculty_ids": row.faculty_ids or [], "program_ids": row.program_ids or [],
        "category_id": str(row.category_id) if row.category_id else None, "status": row.status
    })
    return FAQOut(**payload.model_dump(), id=row.id)

@router.put("/faq/{faq_id}", response_model=FAQOut)
def update_faq(faq_id: UUID, payload: FAQCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = db.query(FAQ).filter(FAQ.id==faq_id).first()
    if not row: raise HTTPException(404, "FAQ not found")
    for k,v in payload.model_dump().items(): setattr(row,k,v)
    db.commit(); db.refresh(row)
    index_faq({
        "id": str(row.id), "question": row.question, "short_answer": row.short_answer,
        "full_answer": row.full_answer, "tags": row.tags or [], "synonyms": row.synonyms or [],
        "faculty_ids": row.faculty_ids or [], "program_ids": row.program_ids or [],
        "category_id": str(row.category_id) if row.category_id else None, "status": row.status
    })
    return FAQOut(**payload.model_dump(), id=row.id)

@router.post("/faq/{faq_id}/publish")
def publish_faq(faq_id: UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = db.query(FAQ).filter(FAQ.id==faq_id).first()
    if not row: raise HTTPException(404, "FAQ not found")
    row.status = "published"; db.commit()
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
    items = (
        db.query(IncomingQuestion)
        .options(joinedload(IncomingQuestion.attachments))
        .order_by(IncomingQuestion.created_at.desc())
        .limit(200)
        .all()
    )

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
    item = db.query(IncomingQuestion).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    old_status = item.status
    old_answer = item.answer

    item.status = status
    item.comment = comment
    item.answer = answer

    if item.status == "done" and answer:
        item.answered_at = datetime.utcnow()
    else:
        item.answered_at = None

    for f in files:
        stored_path, size = save_upload_file(f, str(item.id))
        attachment = IncomingQuestionAttachment(
            question_id=item.id,
            uploader_role="staff",
            original_name=f.filename,
            stored_path=stored_path,
            mime_type=f.content_type,
            file_size=size,
        )
        db.add(attachment)

    db.commit()

    item = (
        db.query(IncomingQuestion)
        .options(joinedload(IncomingQuestion.attachments))
        .filter(IncomingQuestion.id == incoming_id)
        .first()
    )

    if item.telegram_user_id:
        if old_status != "in_progress" and item.status == "in_progress":
            send_telegram_message(
                item.telegram_user_id,
                "Ваше обращение взято в работу."
            )

        if item.status == "done" and item.answer and item.answer != old_answer:
            send_telegram_message(
                item.telegram_user_id,
                f"На ваше обращение поступил ответ:\n\n{item.answer}"
            )

            staff_files = [a for a in item.attachments if a.uploader_role == "staff"]
            if staff_files:
                send_telegram_message(
                    item.telegram_user_id,
                    "К ответу прикреплены файлы:"
                )
                send_staff_attachments(item.telegram_user_id, staff_files)

    return incoming_to_out(item)


@router.get("/faq", response_model=list[FAQOut])
def list_faq(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    rows = db.query(FAQ).order_by(FAQ.question.asc()).all()

    # ВАЖНО: делаем словарь вручную, потому что FAQ — SQLAlchemy, у него нет model_dump()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "question": r.question,
            "short_answer": r.short_answer,
            "full_answer": r.full_answer,
            "category_id": r.category_id,
            "tags": r.tags or [],
            "synonyms": r.synonyms or [],
            "faculty_ids": r.faculty_ids or [],
            "program_ids": r.program_ids or [],
            "course_min": r.course_min,
            "course_max": r.course_max,
            "source_url": r.source_url,
            "status": r.status,
            "valid_from": r.valid_from,
            "valid_until": r.valid_until,
        })

    return out
