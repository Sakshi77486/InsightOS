from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from models.database_models import *

from routes.datasets import router as datasets_router
from routes.reports import router as reports_router
from routes.projects import router as projects_router
from routes.auth import router as auth_router


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="InsightOS API",
    version="0.1.0"
)


# =========================================================
# CORS
# =========================================================
# Allows the frontend running through Live Server
# on localhost / 127.0.0.1 regardless of its port.

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/api/db-health")
def db_health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected"
    }


# =========================================================
# DATASETS
# =========================================================

app.include_router(
    datasets_router,
    prefix="/api/datasets",
    tags=["datasets"]
)


# =========================================================
# REPORTS
# =========================================================

app.include_router(
    reports_router,
    prefix="/api/reports",
    tags=["reports"]
)


# =========================================================
# PROJECTS
# =========================================================

app.include_router(
    projects_router,
    prefix="/api/projects",
    tags=["projects"]
)


# =========================================================
# AUTHENTICATION
# =========================================================

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["auth"]
)