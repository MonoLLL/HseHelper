from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..faq_utils import faq_to_out
from ..models import FAQ, FAQAttachment
from ..schemas import FAQOut

router = APIRouter()

@router.get("/faq/{faq_id}", response_model=FAQOut)
def get_faq(faq_id: UUID, db: Session = Depends(get_db)):
    row = (
        db.query(FAQ)
        .options(joinedload(FAQ.attachments))
        .filter(FAQ.id == faq_id, FAQ.status != "archived")
        .first()
    )
    if not row: raise HTTPException(404, "FAQ not found")
    return faq_to_out(row)


@router.get("/faq/attachments/{attachment_id}/download")
def download_faq_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
):
    attachment = db.query(FAQAttachment).filter(FAQAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = Path(attachment.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )
