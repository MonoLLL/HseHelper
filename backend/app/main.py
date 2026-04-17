from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .admin_setup import ensure_default_admin
from .db import Base, engine
from .routers import admin, events, faq, health, incoming, search

app = FastAPI(title="Uni QA System")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    ensure_default_admin()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Path("/app/uploads").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")
app.include_router(search.router, prefix="/api")
app.include_router(faq.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")
app.include_router(incoming.router, prefix="/api")
