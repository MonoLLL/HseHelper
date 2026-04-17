from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from ..db import get_db
from ..models import IncomingQuestion, IncomingQuestionAttachment
from ..schemas import IncomingChannel, IncomingOut
from ..file_storage import save_upload_file
from datetime import datetime
from pathlib import Path

router = APIRouter()


def attachment_to_out(a):
    return {
        "id": str(a.id),
        "original_name": a.original_name,
        "mime_type": a.mime_type,
        "file_size": a.file_size,
        "uploader_role": a.uploader_role,
        "url": f"/uploads/incoming/{a.question_id}/{Path(a.stored_path).name}",
        "created_at": a.created_at,
    }


def incoming_to_out(row: IncomingQuestion):
    return {
        "id": str(row.id),
        "text": row.text,
        "channel": row.channel,
        "client_id": row.client_id,
        "telegram_user_id": row.telegram_user_id,
        "faculty": row.faculty,
        "course": row.course,
        "status": row.status,
        "comment": row.comment,
        "answer": row.answer,
        "answered_at": row.answered_at,
        "created_at": row.created_at,
        "attachments": [attachment_to_out(a) for a in row.attachments],
    }


@router.post("/incoming", response_model=IncomingOut)
async def create_incoming(
    text: Annotated[str, Form(...)],
    channel: Annotated[IncomingChannel, Form(...)],
    client_id: str | None = Form(None),
    telegram_user_id: str | None = Form(None),
    faculty: str | None = Form(None),
    course: int | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    row = IncomingQuestion(
        text=text,
        channel=channel,
        client_id=client_id,
        telegram_user_id=telegram_user_id,
        faculty=faculty,
        course=course,
        status="new",
        comment=None,
        answer=None,
        answered_at=None,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()

    try:
        for f in files:
            stored_path, size = save_upload_file(f, str(row.id))
            attachment = IncomingQuestionAttachment(
                question_id=row.id,
                uploader_role="student",
                original_name=f.filename or "file",
                stored_path=stored_path,
                mime_type=f.content_type or "application/octet-stream",
                file_size=size,
            )
            db.add(attachment)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()

    row = (
        db.query(IncomingQuestion)
        .options(joinedload(IncomingQuestion.attachments))
        .filter(IncomingQuestion.id == row.id)
        .first()
    )

    return incoming_to_out(row)


@router.get("/incoming", response_model=list[IncomingOut])
def list_incoming(
    client_id: str | None = Query(None, min_length=8),
    telegram_user_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(IncomingQuestion)
        .options(joinedload(IncomingQuestion.attachments))
        .order_by(IncomingQuestion.created_at.desc())
    )

    if client_id:
        query = query.filter(IncomingQuestion.client_id == client_id)
    elif telegram_user_id:
        query = query.filter(IncomingQuestion.telegram_user_id == telegram_user_id)
    else:
        return []

    rows = query.all()

    return [incoming_to_out(row) for row in rows]
