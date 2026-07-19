from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings
from app.enums import UserRole


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=not settings.database_url.startswith("sqlite"),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    from app.models import User  # noqa: F401
    from app.security import hash_password

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == settings.initial_admin_username).first()
        if existing:
            return
        admin = User(
            username=settings.initial_admin_username,
            password_hash=hash_password(settings.initial_admin_password),
            full_name=settings.initial_admin_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
