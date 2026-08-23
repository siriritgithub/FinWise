from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import Base, engine
from sqlalchemy import inspect, text
from fastapi.staticfiles import StaticFiles
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.accounts import router as accounts_router
from app.routers.transactions import router as transactions_router
from app.routers.other_routers import (
    categories_router, budgets_router, recurring_router,
    goals_router, receipts_router, analytics_router, chat_router,
)

settings = get_settings()

app = FastAPI(
    title="FinWise API",
    description="Privacy-first AI-powered personal finance tracker for Indian users.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
for router in [
    auth_router, users_router, accounts_router, transactions_router,
    categories_router, budgets_router, recurring_router,
    goals_router, receipts_router, analytics_router, chat_router,
]:
    app.include_router(router)

# Uploaded profile photos and receipts are served locally during development.
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok", "service": "FinWise API"}


@app.on_event("startup")
def on_startup():
    # Import all models so SQLAlchemy registers them before create_all
    import app.models  # noqa
    Base.metadata.create_all(bind=engine)
    # Lightweight schema upgrades for existing local databases.
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "reset_token_hash" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(128) NULL"))
            if "reset_token_expires_at" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires_at DATETIME NULL"))
            additions = {
                "username": "VARCHAR(100) NULL",
                "phone_number": "VARCHAR(30) NULL",
                "date_of_birth": "DATE NULL",
                "gender": "VARCHAR(30) NULL",
                "occupation": "VARCHAR(120) NULL",
                "country": "VARCHAR(80) NULL",
                "language": "VARCHAR(10) NULL",
                "theme": "VARCHAR(20) NULL",
                "profile_photo_path": "VARCHAR(500) NULL",
            }
            for name, ddl in additions.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
            # Backfill usernames for existing users.
            rows = conn.execute(text("SELECT id,email FROM users WHERE username IS NULL OR username=''"))
            for row in rows: 
                base = str(row.email).split("@")[0][:90]
                conn.execute(text("UPDATE users SET username=:u WHERE id=:id"), {"u": base, "id": row.id})
