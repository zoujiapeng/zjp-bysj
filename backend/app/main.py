from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import initialize_database
from app.routers import (
    audit_logs,
    auth,
    cases,
    dashboard,
    followups,
    organizations,
    referrals,
    reports,
    students,
    users,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "面向学校辅导员与心理老师的学生心理关怀、随访、转介和统计报表系统。"
        "系统用于工作协同与过程留痕，不提供自动心理诊断。"
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(organizations.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(students.router, prefix=api_prefix)
app.include_router(cases.router, prefix=api_prefix)
app.include_router(followups.router, prefix=api_prefix)
app.include_router(referrals.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(audit_logs.router, prefix=api_prefix)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok", "service": "student-care-api"}
