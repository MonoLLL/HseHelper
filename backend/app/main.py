from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .admin_setup import ensure_default_admin
from .db import Base, engine
from .models import Category, FAQ
from .routers import admin, events, faq, health, incoming, search
from .search_service import reindex_faqs

app = FastAPI(title="API")


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


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    ensure_default_admin()

    with Session(engine) as db:
        ensure_default_faq(db)
        rows = db.query(FAQ).filter(FAQ.status == "published").all()
        reindex_faqs(
            [
                {
                    "id": str(row.id),
                    "question": row.question,
                    "short_answer": row.short_answer,
                    "full_answer": row.full_answer,
                    "tags": row.tags or [],
                    "synonyms": row.synonyms or [],
                    "faculty_ids": row.faculty_ids or [],
                    "program_ids": row.program_ids or [],
                    "category_id": str(row.category_id) if row.category_id else None,
                    "status": row.status,
                }
                for row in rows
            ]
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
