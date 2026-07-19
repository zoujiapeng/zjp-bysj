import secrets
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import utcnow
from app.enums import CaseStatus, FollowUpStatus, RiskLevel
from app.models import CareCase, FollowUp, Referral, RiskChange, Student
from app.schemas import FollowUpCompleteCreate


def case_detail_statement(case_id: int):
    return (
        select(CareCase)
        .where(CareCase.id == case_id)
        .options(
            joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(CareCase.student).joinedload(Student.counselor),
            joinedload(CareCase.owner),
            selectinload(CareCase.followups).joinedload(FollowUp.created_by),
            selectinload(CareCase.risk_history).joinedload(RiskChange.changed_by),
            selectinload(CareCase.referrals).joinedload(Referral.requested_by),
            selectinload(CareCase.referrals).joinedload(Referral.assigned_to),
        )
    )


def get_case_detail(db: Session, case_id: int) -> CareCase | None:
    return db.scalars(case_detail_statement(case_id)).unique().first()


def active_case_for_student(db: Session, student_id: int) -> CareCase | None:
    return db.scalar(
        select(CareCase)
        .where(CareCase.student_id == student_id, CareCase.status != CaseStatus.CLOSED)
        .order_by(CareCase.opened_at.desc())
    )


def generate_case_no(db: Session) -> str:
    prefix = utcnow().strftime("CARE-%Y%m%d")
    for _ in range(20):
        value = f"{prefix}-{secrets.token_hex(3).upper()}"
        if db.scalar(select(CareCase.id).where(CareCase.case_no == value)) is None:
            return value
    raise RuntimeError("无法生成唯一个案编号")


def change_risk(
    db: Session,
    case: CareCase,
    *,
    risk_level: RiskLevel,
    reason: str,
    changed_by_id: int,
) -> RiskChange | None:
    if case.risk_level == risk_level:
        return None
    change = RiskChange(
        case_id=case.id,
        from_level=case.risk_level,
        to_level=risk_level,
        reason=reason,
        changed_by_id=changed_by_id,
    )
    case.risk_level = risk_level
    db.add(change)
    return change


def recalculate_next_follow_up(db: Session, case: CareCase) -> datetime | None:
    next_date = db.scalar(
        select(FollowUp.scheduled_at)
        .where(
            FollowUp.case_id == case.id,
            FollowUp.status == FollowUpStatus.PLANNED,
        )
        .order_by(FollowUp.scheduled_at.asc())
        .limit(1)
    )
    case.next_follow_up_at = next_date
    return next_date


def complete_followup(
    db: Session,
    *,
    case: CareCase,
    user_id: int,
    payload: FollowUpCompleteCreate,
    followup: FollowUp | None = None,
) -> tuple[FollowUp, FollowUp | None, RiskChange | None]:
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=409, detail="已结案个案不能继续随访")

    completed_at = payload.completed_at or utcnow()
    if followup is None:
        followup = FollowUp(
            case_id=case.id,
            created_by_id=user_id,
            scheduled_at=completed_at,
        )
        db.add(followup)
    elif followup.status != FollowUpStatus.PLANNED:
        raise HTTPException(status_code=409, detail="该随访任务已经处理")

    followup.created_by_id = user_id
    followup.completed_at = completed_at
    followup.status = payload.status
    followup.method = payload.method
    followup.condition = payload.condition
    followup.issue_tags = payload.issue_tags
    followup.summary = payload.summary
    followup.actions = payload.actions
    followup.contact_result = payload.contact_result
    followup.next_follow_up_at = payload.next_follow_up_at

    risk_change = None
    if payload.risk_level and payload.risk_level != case.risk_level:
        if not payload.risk_reason:
            raise HTTPException(status_code=422, detail="调整风险等级时必须填写原因")
        risk_change = change_risk(
            db,
            case,
            risk_level=payload.risk_level,
            reason=payload.risk_reason,
            changed_by_id=user_id,
        )

    next_task = None
    if payload.next_follow_up_at:
        if payload.next_follow_up_at <= completed_at:
            raise HTTPException(status_code=422, detail="下次随访时间必须晚于本次完成时间")
        next_task = FollowUp(
            case_id=case.id,
            created_by_id=user_id,
            scheduled_at=payload.next_follow_up_at,
            status=FollowUpStatus.PLANNED,
            method=payload.next_method,
            summary="由上次随访自动生成的后续任务",
        )
        db.add(next_task)

    db.flush()
    recalculate_next_follow_up(db, case)
    return followup, next_task, risk_change
