import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .admin_setup import ensure_default_admin
from .db import Base, engine
from .faq_utils import faq_index_doc
from .models import Category, FAQ
from .routers import admin, events, faq, health, incoming, search, users
from .search_service import reindex_faqs

app = FastAPI(title="API")


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    configured = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return configured or ["http://localhost:3000", "http://127.0.0.1:3000"]


def ensure_default_faq(db: Session):
    existing = db.query(FAQ).first()
    if existing:
        return

    category = db.query(Category).filter(Category.name == "Общее").first()
    if not category:
        category = Category(name="Общее", description="Базовые ответы для запуска системы")
        db.add(category)
        db.flush()

    faq = FAQ(
        question="Как задать вопрос в учебный офис?",
        short_answer="Введите вопрос на сайте или отправьте его через Telegram-бота.",
        full_answer=(
            "Вы можете задать вопрос через главную страницу сайта или через Telegram-бота. "
            "Если точного ответа в FAQ нет, система создаст обращение для сотрудника учебного офиса."
        ),
        category_id=category.id,
        tags=["вопрос", "учебный офис", "обращение"],
        synonyms=["как обратиться", "как написать в учебный офис", "как отправить вопрос"],
        faculty_ids=[],
        program_ids=[],
        status="published",
    )
    db.add(faq)
    db.commit()


def ensure_student_user_schema():
    with engine.begin() as connection:
        connection.execute(text("alter table student_users add column if not exists client_id varchar(64)"))
        connection.execute(text("alter table student_users add column if not exists email varchar(255)"))
        connection.execute(text("alter table student_users add column if not exists password_hash varchar(255)"))
        connection.execute(text("alter table student_users alter column telegram_user_id drop not null"))
        connection.execute(
            text("create unique index if not exists ix_student_users_client_id on student_users (client_id)")
        )
        connection.execute(text("create unique index if not exists ix_student_users_email on student_users (email)"))
        connection.execute(text("alter table incoming_questions add column if not exists student_user_id uuid"))
        connection.execute(
            text("create index if not exists ix_incoming_questions_student_user_id on incoming_questions (student_user_id)")
        )


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    ensure_student_user_schema()
    ensure_default_admin()

    with Session(engine) as db:
        ensure_default_faq(db)
        rows = db.query(FAQ).filter(FAQ.status == "published").all()
        reindex_faqs([faq_index_doc(row) for row in rows])


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Path("/app/uploads").mkdir(parents=True, exist_ok=True)
app.include_router(search.router, prefix="/api")
app.include_router(faq.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")
app.include_router(incoming.router, prefix="/api")
app.include_router(users.router, prefix="/api")
