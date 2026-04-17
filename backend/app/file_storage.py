from pathlib import Path
import uuid
from fastapi import UploadFile

UPLOAD_DIR = Path("/app/uploads")

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


def save_upload_file(upload_file: UploadFile, question_id: str) -> tuple[str, int]:
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {upload_file.content_type}")

    target_dir = UPLOAD_DIR / "incoming" / question_id
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = upload_file.filename.replace("/", "_").replace("\\", "_")
    stored_name = f"{uuid.uuid4()}_{safe_name}"
    target_path = target_dir / stored_name

    size = 0
    with target_path.open("wb") as buffer:
        while chunk := upload_file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                target_path.unlink(missing_ok=True)
                raise ValueError("File is too large")
            buffer.write(chunk)

    return str(target_path), size