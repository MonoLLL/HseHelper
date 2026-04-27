import os
from meilisearch import Client
from sqlalchemy.orm import Session

MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "master_key_please_change")
INDEX_NAME = "faq_entries"

client = Client(MEILI_HOST, MEILI_MASTER_KEY)

def ensure_index():
    try:
        client.index(INDEX_NAME).get_settings()
    except Exception:
        client.create_index(INDEX_NAME, {"primaryKey": "id"})
    client.index(INDEX_NAME).update_settings({
        "searchableAttributes":["question","short_answer","full_answer","tags","synonyms"],
        "filterableAttributes":["faculty_ids","program_ids","category_id","status"]
    })

def index_faq(doc):
    ensure_index()
    client.index(INDEX_NAME).add_documents([doc])


def reindex_faqs(rows: list[dict]):
    ensure_index()
    client.index(INDEX_NAME).delete_all_documents()
    if rows:
        client.index(INDEX_NAME).add_documents(rows)

def search(q: str, filters: dict | None = None, limit: int = 5):
    ensure_index()
    meili_filters = []
    if filters and filters.get("faculty_ids"):
        meili_filters.append(f'faculty_ids = "{filters["faculty_ids"]}"')
    filt = " AND ".join(meili_filters) if meili_filters else None
    res = client.index(INDEX_NAME).search(q, {"limit":limit, "filter":filt})
    return res.get("hits", [])
