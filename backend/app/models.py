from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow
from app.enums import (
    CaseStatus,
    Confidentiality,
    FollowUpMethod,
    FollowUpStatus,
    ReferralStatus,
    RiskLevel,
    StudentCondition,
    UserRole,
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="organization")
    students: Mapped[list[Student]] = relationship(back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=32), index=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization | None] = relationship(back_populates="users")
    students_counseled: Mapped[list[Student]] = relationship(
        back_populates="counselor", foreign_keys="Student.counselor_id"
    )
    owned_cases: Mapped[list[CareCase]] = relationship(
        back_populates="owner", foreign_keys="CareCase.owner_id"
    )


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    major: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    class_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    counselor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="students")
    counselor: Mapped[User | None] = relationship(
        back_populates="students_counseled", foreign_keys=[counselor_id]
    )
    cases: Mapped[list[CareCase]] = relationship(
        back_populates="student", order_by="CareCase.opened_at.desc()"
    )


class CareCase(TimestampMixin, Base):
    __tablename__ = "care_cases"
    __table_args__ = (
        Index("ix_care_cases_status_risk", "status", "risk_level"),
        Index(
            "uq_active_case_per_student",
            "student_id",
            unique=True,
            postgresql_where=text("status <> 'CLOSED'"),
            sqlite_where=text("status <> 'CLOSED'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=16), default=RiskLevel.GREEN, index=True
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False, length=24), default=CaseStatus.OPEN, index=True
    )
    source: Mapped[str] = mapped_column(String(100))
    issue_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text)
    confidentiality: Mapped[Confidentiality] = mapped_column(
        Enum(Confidentiality, native_enum=False, length=24),
        default=Confidentiality.NORMAL,
    )
    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[Student] = relationship(back_populates="cases")
    owner: Mapped[User] = relationship(back_populates="owned_cases", foreign_keys=[owner_id])
    followups: Mapped[list[FollowUp]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="FollowUp.scheduled_at.desc()",
    )
    risk_history: Mapped[list[RiskChange]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="RiskChange.created_at.desc()",
    )
    referrals: Mapped[list[Referral]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="Referral.created_at.desc()",
    )


class FollowUp(TimestampMixin, Base):
    __tablename__ = "followups"
    __table_args__ = (Index("ix_followups_status_scheduled", "status", "scheduled_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("care_cases.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, native_enum=False, length=24),
        default=FollowUpStatus.PLANNED,
        index=True,
    )
    method: Mapped[FollowUpMethod | None] = mapped_column(
        Enum(FollowUpMethod, native_enum=False, length=24), nullable=True
    )
    condition: Mapped[StudentCondition] = mapped_column(
        Enum(StudentCondition, native_enum=False, length=24),
        default=StudentCondition.UNKNOWN,
    )
    issue_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_result: Mapped[str | None] = mapped_column(String(200), nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    case: Mapped[CareCase] = relationship(back_populates="followups")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class RiskChange(Base):
    __tablename__ = "risk_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("care_cases.id", ondelete="CASCADE"), index=True
    )
    from_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=16), nullable=True
    )
    to_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=16), index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    changed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    case: Mapped[CareCase] = relationship(back_populates="risk_history")
    changed_by: Mapped[User] = relationship(foreign_keys=[changed_by_id])


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("care_cases.id", ondelete="CASCADE"), index=True
    )
    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ReferralStatus] = mapped_column(
        Enum(ReferralStatus, native_enum=False, length=24),
        default=ReferralStatus.PENDING,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text)
    professional_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[CareCase] = relationship(back_populates="referrals")
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])
