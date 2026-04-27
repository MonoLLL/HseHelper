from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


IncomingChannel = Literal["bot", "site"]
IncomingStatus = Literal["new", "in_progress", "done"]
IncomingSenderRole = Literal["student", "staff"]


class FAQCreate(BaseModel):
    question: str
    short_answer: str
    full_answer: str
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    synonyms: Optional[List[str]] = None
    faculty_ids: Optional[List[str]] = None
    program_ids: Optional[List[str]] = None
    course_min: Optional[int] = None
    course_max: Optional[int] = None
    source_url: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: Optional[str] = "draft"


class FAQOut(FAQCreate):
    id: UUID


class IncomingAttachmentOut(BaseModel):
    id: str
    original_name: str
    mime_type: str
    file_size: int
    uploader_role: str
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncomingMessageAttachmentOut(BaseModel):
    id: str
    original_name: str
    mime_type: str
    file_size: int
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncomingMessageOut(BaseModel):
    id: str
    sender_role: IncomingSenderRole
    text: Optional[str] = None
    created_at: datetime
    attachments: List[IncomingMessageAttachmentOut] = []

    class Config:
        from_attributes = True


class IncomingOut(BaseModel):
    id: UUID
    text: str
    channel: str
    client_id: Optional[str] = None
    telegram_user_id: str | None
    faculty: str | None
    course: int | None
    status: str
    comment: str | None
    created_at: datetime
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    attachments: List[IncomingAttachmentOut] = []
    messages: List[IncomingMessageOut] = []

    class Config:
        from_attributes = True

