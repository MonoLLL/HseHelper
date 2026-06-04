import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, or_
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import foreign, relationship
from sqlalchemy.sql import func

from .db import Base
from .time_utils import now_yekaterinburg


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)


class FAQ(Base):
    __tablename__ = "faq_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(String(255), nullable=False)
    short_answer = Column(String(400), nullable=False)
    full_answer = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    synonyms = Column(ARRAY(String), nullable=True)
    faculty_ids = Column(ARRAY(String), nullable=True)
    program_ids = Column(ARRAY(String), nullable=True)
    course_min = Column(Integer, nullable=True)
    course_max = Column(Integer, nullable=True)
    source_url = Column(String(500), nullable=True)
    status = Column(String(32), default="published")
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    attachments = relationship(
        "FAQAttachment",
        backref="faq",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: FAQAttachment.created_at.asc(),
    )


class FAQAttachment(Base):
    __tablename__ = "faq_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    faq_id = Column(UUID(as_uuid=True), ForeignKey("faq_entries.id", ondelete="CASCADE"), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False, server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    campus = Column(String(128))
    faculty = Column(String(128))
    program = Column(String(128))
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=True)
    type = Column(String(64), nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="editor")
    is_active = Column(Boolean, default=True)


class StudentUser(Base):
    __tablename__ = "student_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(64), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    telegram_user_id = Column(String(64), unique=True, nullable=True, index=True)
    telegram_username = Column(String(128), nullable=True)
    telegram_first_name = Column(String(128), nullable=True)
    telegram_last_name = Column(String(128), nullable=True)
    full_name = Column(String(255), nullable=False)
    faculty = Column(String(128), nullable=True)
    course = Column(Integer, nullable=True)
    group_name = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False)
    updated_at = Column(DateTime, default=now_yekaterinburg, onupdate=now_yekaterinburg, nullable=False)


class IncomingQuestion(Base):
    __tablename__ = "incoming_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    channel = Column(String(16), nullable=False)  # bot | site
    student_user_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id"), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    telegram_user_id = Column(String(64), nullable=True)
    faculty = Column(String(64), nullable=True)
    course = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, default="new")
    comment = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False)

    student_user = relationship(
        "StudentUser",
        primaryjoin=lambda: or_(
            foreign(IncomingQuestion.student_user_id) == StudentUser.id,
            foreign(IncomingQuestion.telegram_user_id) == StudentUser.telegram_user_id,
            foreign(IncomingQuestion.client_id) == StudentUser.client_id,
        ),
        uselist=False,
        viewonly=True,
    )
    attachments = relationship(
        "IncomingQuestionAttachment",
        backref="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="IncomingQuestionAttachment.created_at.asc()",
    )
    messages = relationship(
        "IncomingMessage",
        backref="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="IncomingMessage.created_at.asc()",
    )


class IncomingQuestionAttachment(Base):
    __tablename__ = "incoming_question_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("incoming_questions.id", ondelete="CASCADE"), nullable=False)
    uploader_role = Column(String(16), nullable=False)  # student / staff
    original_name = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False, server_default=func.now())


class IncomingMessage(Base):
    __tablename__ = "incoming_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("incoming_questions.id", ondelete="CASCADE"), nullable=False)
    sender_role = Column(String(16), nullable=False)  # student / staff
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False, server_default=func.now())

    attachments = relationship(
        "IncomingMessageAttachment",
        backref="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="IncomingMessageAttachment.created_at.asc()",
    )


class IncomingMessageAttachment(Base):
    __tablename__ = "incoming_message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("incoming_messages.id", ondelete="CASCADE"), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=now_yekaterinburg, nullable=False, server_default=func.now())
