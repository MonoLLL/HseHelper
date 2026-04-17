from .db import Base, engine, SessionLocal
from .models import Category, FAQ, Event, AdminUser
from .auth import hash_password
from datetime import datetime, timedelta
from .search_service import index_faq

def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    cat = Category(name="Оплата", description="Вопросы оплаты обучения")
    db.add(cat); db.commit(); db.refresh(cat)
    f = FAQ(
        question="Срок оплаты обучения",
        short_answer="Оплата за семестр до 15 ноября.",
        full_answer="Оплата в личном кабинете. Реквизиты на странице деканата. При просрочке начисляется пеня.",
        category_id=cat.id, tags=["оплата","сроки"], synonyms=["когда платить","оплата дедлайн"],
        faculty_ids=["FIT"], program_ids=["ISIT"], course_min=1, course_max=4, status="published"
    )
    db.add(f)
    e = Event(
        title="Срок оплаты осеннего семестра",
        description="Оплата за осенний семестр",
        date_start=datetime.utcnow()+timedelta(days=20), type="payment_deadline", faculty="FIT", campus="Main"
    )
    db.add(e)
    admin = AdminUser(email="admin@uni.local", name="Admin", password_hash=hash_password("admin123"), role="admin")
    db.add(admin)
    db.commit()
    index_faq({
        "id": str(f.id), "question": f.question, "short_answer": f.short_answer,
        "full_answer": f.full_answer, "tags": f.tags or [], "synonyms": f.synonyms or [],
        "faculty_ids": f.faculty_ids or [], "program_ids": f.program_ids or [],
        "category_id": str(f.category_id) if f.category_id else None, "status": f.status
    })
    db.close()

if __name__ == "__main__":
    run()
