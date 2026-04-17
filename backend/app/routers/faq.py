from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from ..db import get_db
from ..models import FAQ
from ..schemas import FAQOut

router = APIRouter()

@router.get("/faq/{faq_id}", response_model=FAQOut)
def get_faq(faq_id: UUID, db: Session = Depends(get_db)):
    row = db.query(FAQ).filter(FAQ.id==faq_id, FAQ.status!="archived").first()
    if not row: raise HTTPException(404, "FAQ not found")
    return FAQOut(
        id=row.id, question=row.question, short_answer=row.short_answer, full_answer=row.full_answer,
        category_id=row.category_id, tags=row.tags, synonyms=row.synonyms,
        faculty_ids=row.faculty_ids, program_ids=row.program_ids,
        course_min=row.course_min, course_max=row.course_max, source_url=row.source_url,
        valid_from=row.valid_from, valid_until=row.valid_until, status=row.status
    )
