from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

IncomingChannel = Literal["bot", "site"]
IncomingStatus = Literal["new", "in_progress", "done"]

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


class IncomingCreate(BaseModel):
    text: str
    channel: IncomingChannel
    telegram_user_id: str | None = None
    faculty: str | None = None
    course: int | None = None
    client_id: Optional[str] = None

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
    attachments: List[IncomingAttachmentOut] = []
    class Config:
        from_attributes = True
    

class IncomingUpdate(BaseModel):
    status: Optional[IncomingStatus] = None
    comment: Optional[str] = None
    answer: Optional[str] = None
