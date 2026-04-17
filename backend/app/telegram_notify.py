import os
from pathlib import Path
import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN")


def send_telegram_message(chat_id: str | None, text: str):
    if not BOT_TOKEN or not chat_id or not text:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                url,
                json={
                    "chat_id": str(chat_id),
                    "text": text,
                },
            )
            print("[telegram_notify] send message:", resp.status_code, resp.text)
    except Exception as e:
        print(f"[telegram_notify] send message error: {e}")


def send_telegram_file(chat_id: str | None, file_path: str, filename: str, mime_type: str | None = None):
    if not BOT_TOKEN or not chat_id or not file_path:
        print("[telegram_notify] skip file: missing token/chat_id/file_path")
        return

    path = Path(file_path)
    if not path.exists():
        print(f"[telegram_notify] file not found: {file_path}")
        return

    is_image = (mime_type or "").startswith("image/")
    method = "sendPhoto" if is_image else "sendDocument"
    field_name = "photo" if is_image else "document"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    try:
        with httpx.Client(timeout=60) as client:
            with open(path, "rb") as f:
                files = {
                    field_name: (filename, f, mime_type or "application/octet-stream")
                }
                data = {
                    "chat_id": str(chat_id),
                    "caption": filename,
                }
                resp = client.post(url, data=data, files=files)
                print("[telegram_notify] send file:", resp.status_code, resp.text)
    except Exception as e:
        print(f"[telegram_notify] send file error: {e}")


def send_staff_attachments(chat_id: str | None, attachments: list):
    if not BOT_TOKEN or not chat_id or not attachments:
        return

    for a in attachments:
        try:
            send_telegram_file(
                chat_id=chat_id,
                file_path=a.stored_path,
                filename=a.original_name,
                mime_type=a.mime_type,
            )
        except Exception as e:
            print(f"[telegram_notify] attachment error: {e}")