from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db, utcnow
from app.dependencies import get_current_user
from app.enums import CaseStatus, FollowUpStatus
from app.models import CareCase, FollowUp, Student, User
from app.permissions import case_scope_condition, ensure_case_modify
from app.schemas import (
    FollowUpCompleteCreate,
    FollowUpOut,
    FollowUpPlanCreate,
    MessageResponse,
    Page,
)
from app.serializers import followup_out
from app.services.case_service import complete_followup, get_case_detail, recalculate_next_follow_up

router = APIRouter(tags=["随访"])


def _list_statement(current_user: User):
    return (
        select(FollowUp)
        .join(FollowUp.case)
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
        .options(
            joinedload(FollowUp.case).joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(FollowUp.created_by),
        )
    )


@router.get("/followups", response_model=Page[FollowUpOut])
def list_followups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: FollowUpStatus | None = None,
    case_id: int | None = None,
    overdue: bool | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = _list_statement(current_user)
    count_stmt = (
        select(func.count(FollowUp.id))
        .join(FollowUp.case)
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
    )
    conditions = []
    if status:
        conditions.append(FollowUp.status == status)
    if case_id:
        conditions.append(FollowUp.case_id == case_id)
    if overdue is True:
        conditions.extend(
            [FollowUp.status == FollowUpStatus.PLANNED, FollowUp.scheduled_at < utcnow()]
        )
    elif overdue is False:
        conditions.append(
            (FollowUp.status != FollowUpStatus.PLANNED) | (FollowUp.scheduled_at >= utcnow())
        )
    if scheduled_from:
        conditions.append(FollowUp.scheduled_at >= scheduled_from)
    if scheduled_to:
        conditions.append(FollowUp.scheduled_at <= scheduled_to)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = db.scalar(count_stmt) or 0
    pending_first = sql_case((FollowUp.status == FollowUpStatus.PLANNED, 0), else_=1)
    items = db.scalars(
        stmt.order_by(pending_first, FollowUp.scheduled_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page(
        items=[followup_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/cases/{case_id}/followups/plans", response_model=FollowUpOut, status_code=201)
def create_followup_plan(
    case_id: int,
    payload: FollowUpPlanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=409, detail="已结案个案不能创建随访计划")
    followup = FollowUp(
        case_id=case.id,
        created_by_id=current_user.id,
        scheduled_at=payload.scheduled_at,
        status=FollowUpStatus.PLANNED,
        method=payload.method,
        summary=payload.purpose,
    )
    db.add(followup)
    db.flush()
    recalculate_next_follow_up(db, case)
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_FOLLOWUP_PLAN",
        resource_type="FOLLOWUP",
        resource_id=followup.id,
        summary=f"为个案 {case.case_no} 创建随访计划",
        request=request,
        extra_data={"scheduled_at": payload.scheduled_at.isoformat()},
    )
    db.commit()
    item = db.scalar(_list_statement(current_user).where(FollowUp.id == followup.id))
    return followup_out(item)


@router.post("/followups/{followup_id}/complete", response_model=FollowUpOut)
def complete_planned_followup(
    followup_id: int,
    payload: FollowUpCompleteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    followup = db.get(FollowUp, followup_id)
    if followup is None:
        raise HTTPException(status_code=404, detail="随访任务不存在")
    case = ensure_case_modify(get_case_detail(db, followup.case_id), current_user)
    result, next_task, risk_change = complete_followup(
        db,
        case=case,
        user_id=current_user.id,
        payload=payload,
        followup=followup,
    )
    add_audit_log(
        db,
        actor=current_user,
        action="COMPLETE_FOLLOWUP",
        resource_type="FOLLOWUP",
        resource_id=result.id,
        summary=f"完成 {case.student.name} 的随访，结果 {payload.status.value}",
        request=request,
        extra_data={
            "condition": payload.condition.value,
            "next_followup_id": next_task.id if next_task else None,
            "risk_changed": risk_change is not None,
        },
    )
    db.commit()
    item = db.scalar(_list_statement(current_user).where(FollowUp.id == result.id))
    return followup_out(item)


@router.post("/cases/{case_id}/followups/complete", response_model=FollowUpOut, status_code=201)
def complete_ad_hoc_followup(
    case_id: int,
    payload: FollowUpCompleteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    result, next_task, risk_change = complete_followup(
        db,
        case=case,
        user_id=current_user.id,
        payload=payload,
    )
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_FOLLOWUP_RECORD",
        resource_type="FOLLOWUP",
        resource_id=result.id,
        summary=f"补录 {case.student.name} 的随访记录",
        request=request,
        extra_data={
            "condition": payload.condition.value,
            "next_followup_id": next_task.id if next_task else None,
            "risk_changed": risk_change is not None,
        },
    )
    db.commit()
    item = db.scalar(_list_statement(current_user).where(FollowUp.id == result.id))
    return followup_out(item)


@router.post("/followups/{followup_id}/cancel", response_model=MessageResponse)
def cancel_followup(
    followup_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    followup = db.get(FollowUp, followup_id)
    if followup is None:
        raise HTTPException(status_code=404, detail="随访任务不存在")
    case = ensure_case_modify(get_case_detail(db, followup.case_id), current_user)
    if followup.status != FollowUpStatus.PLANNED:
        raise HTTPException(status_code=409, detail="只有待随访任务可以取消")
    followup.status = FollowUpStatus.CANCELLED
    db.flush()
    recalculate_next_follow_up(db, case)
    add_audit_log(
        db,
        actor=current_user,
        action="CANCEL_FOLLOWUP",
        resource_type="FOLLOWUP",
        resource_id=followup.id,
        summary=f"取消个案 {case.case_no} 的随访计划",
        request=request,
    )
    db.commit()
    return MessageResponse(message="随访任务已取消")
