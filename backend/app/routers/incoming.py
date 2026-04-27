from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..file_storage import save_upload_file
from ..models import (
    IncomingMessage,
    IncomingMessageAttachment,
    IncomingQuestion,
    IncomingQuestionAttachment,
)
from ..schemas import IncomingChannel, IncomingOut


router = APIRouter()


def attachment_to_out(attachment: IncomingQuestionAttachment):
    return {
        "id": str(attachment.id),
        "original_name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "uploader_role": attachment.uploader_role,
        "url": f"/api/incoming/attachments/question/{attachment.id}/download",
        "created_at": attachment.created_at,
    }


def message_attachment_to_out(attachment: IncomingMessageAttachment):
    return {
        "id": str(attachment.id),
        "original_name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "uploader_role": attachment.message.sender_role,
        "url": f"/api/incoming/attachments/message/{attachment.id}/download",
        "created_at": attachment.created_at,
    }


def message_to_out(message: IncomingMessage):
    return {
        "id": str(message.id),
        "sender_role": message.sender_role,
        "text": message.text,
        "created_at": message.created_at,
        "attachments": [message_attachment_to_out(attachment) for attachment in message.attachments],
    }


def build_legacy_messages(row: IncomingQuestion):
    messages = []

    student_attachments = [attachment_to_out(attachment) for attachment in row.attachments if attachment.uploader_role == "student"]
    if row.text or student_attachments:
        messages.append(
            {
                "id": f"legacy-student-{row.id}",
                "sender_role": "student",
                "text": row.text,
                "created_at": row.created_at,
                "attachments": student_attachments,
            }
        )

    staff_attachments = [attachment_to_out(attachment) for attachment in row.attachments if attachment.uploader_role == "staff"]
    if row.answer or staff_attachments:
        messages.append(
            {
                "id": f"legacy-staff-{row.id}",
                "sender_role": "staff",
                "text": row.answer,
                "created_at": row.answered_at or row.created_at,
                "attachments": staff_attachments,
            }
        )

    return messages


def incoming_to_out(row: IncomingQuestion):
    flat_attachments = [attachment_to_out(attachment) for attachment in row.attachments]
    for message in row.messages:
        flat_attachments.extend(message_attachment_to_out(attachment) for attachment in message.attachments)

    messages = [message_to_out(message) for message in row.messages] if row.messages else build_legacy_messages(row)

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
        "closed_at": row.answered_at if row.status == "done" else None,
        "created_at": row.created_at,
        "attachments": flat_attachments,
        "messages": messages,
    }


def incoming_query(db: Session):
    return db.query(IncomingQuestion).options(
        joinedload(IncomingQuestion.attachments),
        joinedload(IncomingQuestion.messages).joinedload(IncomingMessage.attachments),
    )


def create_message(
    db: Session,
    item: IncomingQuestion,
    sender_role: str,
    text: str | None,
    files: list[UploadFile],
):
    message_text = (text or "").strip() or None
    if not message_text and not files:
        raise HTTPException(status_code=400, detail="Message text or files are required")

    message = IncomingMessage(
        question_id=item.id,
        sender_role=sender_role,
        text=message_text,
        created_at=datetime.utcnow(),
    )
    db.add(message)
    db.flush()

    for upload in files:
        try:
            stored_path, size = save_upload_file(upload, str(item.id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        db.add(
            IncomingMessageAttachment(
                message_id=message.id,
                original_name=upload.filename or "file",
                stored_path=stored_path,
                mime_type=upload.content_type or "application/octet-stream",
                file_size=size,
            )
        )

    return message


def require_student_access(item: IncomingQuestion, client_id: str | None, telegram_user_id: str | None):
    if client_id and item.client_id == client_id:
        return
    if telegram_user_id and item.telegram_user_id == telegram_user_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/incoming/attachments/question/{attachment_id}/download")
def download_question_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
):
    attachment = db.query(IncomingQuestionAttachment).filter(IncomingQuestionAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = Path(attachment.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )


@router.get("/incoming/attachments/message/{attachment_id}/download")
def download_message_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
):
    attachment = db.query(IncomingMessageAttachment).filter(IncomingMessageAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = Path(attachment.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )


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
        create_message(db, row, "student", text, files)
    except HTTPException:
        db.rollback()
        raise

    db.commit()
    row = incoming_query(db).filter(IncomingQuestion.id == row.id).first()
    return incoming_to_out(row)


@router.get("/incoming", response_model=list[IncomingOut])
def list_incoming(
    client_id: str | None = Query(None, min_length=8),
    telegram_user_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = incoming_query(db).order_by(IncomingQuestion.created_at.desc())

    if client_id:
        query = query.filter(IncomingQuestion.client_id == client_id)
    elif telegram_user_id:
        query = query.filter(IncomingQuestion.telegram_user_id == telegram_user_id)
    else:
        return []

    return [incoming_to_out(row) for row in query.all()]


@router.post("/incoming/{incoming_id}/messages", response_model=IncomingOut)
async def append_student_message(
    incoming_id: str,
    text: str | None = Form(None),
    client_id: str | None = Form(None),
    telegram_user_id: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    require_student_access(item, client_id, telegram_user_id)

    if item.status == "done":
        raise HTTPException(status_code=400, detail="Incoming question is already closed")

    try:
        create_message(db, item, "student", text, files)
    except HTTPException:
        db.rollback()
        raise

    db.commit()
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    return incoming_to_out(item)


@router.post("/incoming/{incoming_id}/close", response_model=IncomingOut)
def close_incoming(
    incoming_id: str,
    client_id: str | None = Form(None),
    telegram_user_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    require_student_access(item, client_id, telegram_user_id)

    item.status = "done"
    item.answered_at = datetime.utcnow()
    db.commit()

    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    return incoming_to_out(item)
