from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from ..db import get_db
from ..faq_utils import faq_to_search_result
from ..models import FAQ
from ..search_service import search as meili_search

router = APIRouter()

@router.get("/search")
def search(q: str = Query(..., min_length=1), faculty: str | None = None, db: Session = Depends(get_db)):
    hits = meili_search(q, {"faculty_ids": faculty} if faculty else {})
    if hits:
        hit_ids = []
        for hit in hits:
            try:
                hit_ids.append(UUID(str(hit.get("id"))))
            except (TypeError, ValueError):
                continue

        rows = (
            db.query(FAQ)
            .options(joinedload(FAQ.attachments))
            .filter(FAQ.id.in_(hit_ids), FAQ.status == "published")
            .all()
            if hit_ids
            else []
        )
        rows_by_id = {str(row.id): row for row in rows}
        results = [
            faq_to_search_result(rows_by_id[str(hit.get("id"))], hit.get("_rankingScore", 1.0))
            for hit in hits
            if str(hit.get("id")) in rows_by_id
        ]
        if results:
            return results

    like = f"%{q.lower()}%"
    rows = (
        db.query(FAQ)
        .options(joinedload(FAQ.attachments))
        .filter(FAQ.status == "published")
        .filter((FAQ.question.ilike(like)) | (FAQ.short_answer.ilike(like)) | (FAQ.full_answer.ilike(like)))
        .limit(5)
        .all()
    )
    return [faq_to_search_result(row, 0.1) for row in rows]
