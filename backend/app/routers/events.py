from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from ..models import Event

router = APIRouter()

@router.get("/events")
def events(type: str | None = None, date_from: str | None = None, date_to: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Event)
    if type: q = q.filter(Event.type==type)
    if date_from: q = q.filter(Event.date_start >= datetime.fromisoformat(date_from))
    if date_to: q = q.filter(Event.date_start <= datetime.fromisoformat(date_to))
    rows = q.order_by(Event.date_start.asc()).limit(100).all()
    return [{
        "id": str(r.id), "title": r.title, "description": r.description,
        "date_start": r.date_start.isoformat(),
        "date_end": r.date_end.isoformat() if r.date_end else None,
        "type": r.type, "faculty": r.faculty, "program": r.program, "campus": r.campus
    } for r in rows]
