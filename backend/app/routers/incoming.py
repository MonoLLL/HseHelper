from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..file_storage import save_upload_file
from ..models import (
    IncomingMessage,
    IncomingMessageAttachment,
    IncomingQuestion,
    IncomingQuestionAttachment,
    StudentUser,
)
from ..schemas import IncomingChannel, IncomingOut
from ..time_utils import now_yekaterinburg
from .users import get_student_from_authorization


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
        "student_user": row.student_user,
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
        joinedload(IncomingQuestion.student_user),
        joinedload(IncomingQuestion.attachments),
        joinedload(IncomingQuestion.messages).joinedload(IncomingMessage.attachments),
    )


def get_student_by_telegram(db: Session, telegram_user_id: str | None) -> StudentUser | None:
    if not telegram_user_id:
        return None
    return db.query(StudentUser).filter(StudentUser.telegram_user_id == telegram_user_id).first()


def filter_by_student_identity(query, student_user: StudentUser, telegram_user_id: str | None = None):
    linked_telegram_id = telegram_user_id or student_user.telegram_user_id
    filters = [IncomingQuestion.student_user_id == student_user.id]
    if linked_telegram_id:
        filters.append(
            and_(
                IncomingQuestion.telegram_user_id == linked_telegram_id,
                IncomingQuestion.student_user_id.is_(None),
            )
        )
    return query.filter(or_(*filters))


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
        created_at=now_yekaterinburg(),
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


def require_student_access(
    item: IncomingQuestion,
    client_id: str | None,
    telegram_user_id: str | None,
    student_user: StudentUser | None = None,
):
    if student_user:
        if item.student_user_id == student_user.id:
            return
        if (
            item.student_user_id is None
            and student_user.telegram_user_id
            and item.telegram_user_id == student_user.telegram_user_id
        ):
            return
        raise HTTPException(status_code=403, detail="Forbidden")

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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    student_user = get_student_from_authorization(authorization, db, required=False)

    if channel == "site":
        if not student_user:
            raise HTTPException(status_code=401, detail="Registration is required")
        client_id = None
        faculty = student_user.faculty
        course = student_user.course

    if telegram_user_id:
        user = get_student_by_telegram(db, telegram_user_id)
        if user:
            if not student_user:
                student_user = user
            faculty = faculty or user.faculty
            course = course or user.course
    elif client_id:
        user = db.query(StudentUser).filter(StudentUser.client_id == client_id).first()
        if user:
            faculty = faculty or user.faculty
            course = course or user.course

    row = IncomingQuestion(
        text=text,
        channel=channel,
        student_user_id=student_user.id if student_user else None,
        client_id=client_id,
        telegram_user_id=telegram_user_id,
        faculty=faculty,
        course=course,
        status="new",
        comment=None,
        answer=None,
        answered_at=None,
        created_at=now_yekaterinburg(),
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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    query = incoming_query(db).order_by(IncomingQuestion.created_at.desc())
    student_user = get_student_from_authorization(authorization, db, required=False)

    if student_user:
        query = filter_by_student_identity(query, student_user)
    elif client_id:
        query = query.filter(IncomingQuestion.client_id == client_id)
    elif telegram_user_id:
        telegram_user = get_student_by_telegram(db, telegram_user_id)
        if telegram_user:
            query = filter_by_student_identity(query, telegram_user, telegram_user_id)
        else:
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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    student_user = get_student_from_authorization(authorization, db, required=False)
    if not student_user:
        student_user = get_student_by_telegram(db, telegram_user_id)
    require_student_access(item, client_id, telegram_user_id, student_user)

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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incoming question not found")

    student_user = get_student_from_authorization(authorization, db, required=False)
    if not student_user:
        student_user = get_student_by_telegram(db, telegram_user_id)
    require_student_access(item, client_id, telegram_user_id, student_user)

    item.status = "done"
    item.answered_at = now_yekaterinburg()
    db.commit()

    item = incoming_query(db).filter(IncomingQuestion.id == incoming_id).first()
    return incoming_to_out(item)
