from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import FAQ
from ..search_service import search as meili_search

router = APIRouter()

@router.get("/search")
def search(q: str = Query(..., min_length=1), faculty: str | None = None, db: Session = Depends(get_db)):
    hits = meili_search(q, {"faculty_ids": faculty} if faculty else {})
    if hits:
        return [{"id": h["id"], "question": h["question"], "short_answer": h["short_answer"], "score": h.get("_rankingScore",1.0)} for h in hits]
    like = f"%{q.lower()}%"
    rows = db.query(FAQ).filter(FAQ.status=="published").filter((FAQ.question.ilike(like)) | (FAQ.short_answer.ilike(like)) | (FAQ.full_answer.ilike(like))).limit(5).all()
    return [{"id": str(r.id), "question": r.question, "short_answer": r.short_answer, "score": 0.1} for r in rows]
