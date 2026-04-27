import os
import mimetypes
import httpx
from config import API_BASE


DEFAULT_CANDIDATE_BASES = (
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://backend:8000",
)

_preferred_api_base = None


def _candidate_bases() -> list[str]:
    values = []

    if API_BASE:
        values.append(API_BASE.rstrip("/"))

    for item in DEFAULT_CANDIDATE_BASES:
        if item not in values:
            values.append(item)

    return values


def get_api_base() -> str:
    return _preferred_api_base or _candidate_bases()[0]


def build_api_url(path: str) -> str:
    return f"{get_api_base()}{path}"


async def _request(method: str, path: str, **kwargs):
    global _preferred_api_base

    last_error = None

    for base in _candidate_bases():
        try:
            async with httpx.AsyncClient(timeout=kwargs.pop("timeout", 30)) as client:
                response = await client.request(method, f"{base}{path}", **kwargs)
                response.raise_for_status()
                _preferred_api_base = base
                return response
        except httpx.RequestError as exc:
            last_error = exc
            continue
        except httpx.HTTPStatusError as exc:
            _preferred_api_base = base
            raise exc

    if last_error:
        raise last_error

    raise RuntimeError("API request failed without a concrete error")


async def search_faq(query: str):
    response = await _request("GET", "/api/search", params={"q": query}, timeout=30)
    return response.json()


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

        response = await _request(
            "POST",
            "/api/incoming",
            data=data,
            files=files if files else None,
            timeout=60,
        )
        return response.json()
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
    response = await _request(
        "GET",
        "/api/incoming",
        params={"telegram_user_id": telegram_user_id},
        timeout=30,
    )
    return response.json()


async def append_incoming_message(
    incoming_id: str,
    telegram_user_id: str,
    text: str | None = None,
    file_paths: list[dict] | None = None,
):
    data = {"telegram_user_id": telegram_user_id}
    if text and text.strip():
        data["text"] = text.strip()

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

        response = await _request(
            "POST",
            f"/api/incoming/{incoming_id}/messages",
            data=data,
            files=files if files else None,
            timeout=60,
        )
        return response.json()
    finally:
        for f in opened:
            f.close()

        if file_paths:
            for item in file_paths:
                try:
                    os.remove(item["path"])
                except OSError:
                    pass


async def close_incoming(incoming_id: str, telegram_user_id: str):
    response = await _request(
        "POST",
        f"/api/incoming/{incoming_id}/close",
        data={"telegram_user_id": telegram_user_id},
        timeout=30,
    )
    return response.json()
