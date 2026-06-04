from .models import FAQ, FAQAttachment


def faq_attachment_to_out(attachment: FAQAttachment):
    return {
        "id": str(attachment.id),
        "original_name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "url": f"/api/faq/attachments/{attachment.id}/download",
        "created_at": attachment.created_at,
    }


def faq_to_out(row: FAQ):
    return {
        "id": row.id,
        "question": row.question,
        "short_answer": row.short_answer,
        "full_answer": row.full_answer,
        "category_id": row.category_id,
        "tags": row.tags or [],
        "synonyms": row.synonyms or [],
        "faculty_ids": row.faculty_ids or [],
        "program_ids": row.program_ids or [],
        "course_min": row.course_min,
        "course_max": row.course_max,
        "source_url": row.source_url,
        "valid_from": row.valid_from,
        "valid_until": row.valid_until,
        "status": row.status,
        "attachments": [faq_attachment_to_out(attachment) for attachment in row.attachments],
    }


def faq_to_search_result(row: FAQ, score: float = 1.0):
    return {
        "id": str(row.id),
        "question": row.question,
        "short_answer": row.short_answer,
        "full_answer": row.full_answer,
        "score": score,
        "attachments": [faq_attachment_to_out(attachment) for attachment in row.attachments],
    }


def faq_index_doc(row: FAQ):
    return {
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
