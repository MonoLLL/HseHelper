import os
import mimetypes
import httpx
from config import API_BASE


async def search_faq(query: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_BASE}/api/search", params={"q": query})
        r.raise_for_status()
        return r.json()


async def create_incoming(text: str, telegram_user_id: str, file_paths: list[dict] | None = None):
    data = {
        "text": text,
        "channel": "bot",
        "telegram_user_id": telegram_user_id,
    }

    files = []
    opened = []

    try:
        if file_paths:
            for item in file_paths:
                path = item["path"]
                filename = item["filename"]
                mime_type = item.get("mime_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"

                f = open(path, "rb")
                opened.append(f)
                files.append(("files", (filename, f, mime_type)))

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{API_BASE}/api/incoming",
                data=data,
                files=files if files else None,
            )
            r.raise_for_status()
            return r.json()
    finally:
        for f in opened:
            f.close()

        if file_paths:
            for item in file_paths:
                try:
                    os.remove(item["path"])
                except OSError:
                    pass


async def list_incoming(telegram_user_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{API_BASE}/api/incoming",
            params={"telegram_user_id": telegram_user_id},
        )
        r.raise_for_status()
        return r.json()
