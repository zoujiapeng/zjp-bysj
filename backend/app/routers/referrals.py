from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db, utcnow
from app.dependencies import get_current_user
from app.enums import CaseStatus, Confidentiality, ReferralStatus, UserRole
from app.models import CareCase, Referral, Student, User
from app.permissions import case_scope_condition, ensure_case_modify, ensure_user_exists
from app.schemas import Page, ReferralCreate, ReferralOut, ReferralUpdate
from app.serializers import referral_out
from app.services.case_service import get_case_detail

router = APIRouter(tags=["转介"])


def _list_statement(current_user: User):
    return (
        select(Referral)
        .join(Referral.case)
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
        .options(
            joinedload(Referral.case).joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(Referral.requested_by),
            joinedload(Referral.assigned_to),
        )
    )


def _safe_referral(item: Referral, current_user: User) -> ReferralOut:
    result = referral_out(item)
    if (
        current_user.role == UserRole.ADMIN
        and item.case.confidentiality == Confidentiality.RESTRICTED
    ):
        result.reason = "受限内容，仅负责人和心理老师可见"
        result.professional_note = None
    return result


@router.get("/referrals", response_model=Page[ReferralOut])
def list_referrals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ReferralStatus | None = None,
    assigned_to_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = _list_statement(current_user)
    count_stmt = (
        select(func.count(Referral.id))
        .join(Referral.case)
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
    )
    conditions = []
    if status:
        conditions.append(Referral.status == status)
    if assigned_to_id:
        conditions.append(Referral.assigned_to_id == assigned_to_id)
    if current_user.role == UserRole.PSYCHOLOGIST:
        conditions.append(
            (Referral.assigned_to_id.is_(None)) | (Referral.assigned_to_id == current_user.id)
        )
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(Referral.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique()
    return Page(
        items=[_safe_referral(item, current_user) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/cases/{case_id}/referrals", response_model=ReferralOut, status_code=201)
def create_referral(
    case_id: int,
    payload: ReferralCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=409, detail="已结案个案不能发起转介")
    existing = db.scalar(
        select(Referral.id).where(
            Referral.case_id == case.id,
            Referral.status.in_([ReferralStatus.PENDING, ReferralStatus.ACCEPTED]),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="该个案已有处理中转介")
    assignee = None
    if payload.assigned_to_id:
        assignee = ensure_user_exists(db, payload.assigned_to_id, role=UserRole.PSYCHOLOGIST)
    referral = Referral(
        case_id=case.id,
        requested_by_id=current_user.id,
        assigned_to_id=assignee.id if assignee else None,
        status=ReferralStatus.PENDING,
        reason=payload.reason.strip(),
    )
    case.status = CaseStatus.REFERRED
    db.add(referral)
    db.flush()
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_REFERRAL",
        resource_type="REFERRAL",
        resource_id=referral.id,
        summary=f"为个案 {case.case_no} 发起心理中心转介",
        request=request,
    )
    db.commit()
    item = db.scalar(_list_statement(current_user).where(Referral.id == referral.id))
    return _safe_referral(item, current_user)


@router.patch("/referrals/{referral_id}", response_model=ReferralOut)
def update_referral(
    referral_id: int,
    payload: ReferralUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        raise HTTPException(status_code=403, detail="只有心理老师可以处理转介")
    referral = db.scalar(
        select(Referral)
        .where(Referral.id == referral_id)
        .options(joinedload(Referral.case).joinedload(CareCase.student))
    )
    if referral is None:
        raise HTTPException(status_code=404, detail="转介记录不存在")
    if (
        current_user.role == UserRole.PSYCHOLOGIST
        and referral.assigned_to_id is not None
        and referral.assigned_to_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="该转介已分配给其他心理老师")
    if referral.status in {ReferralStatus.COMPLETED, ReferralStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="该转介已经处理完成")
    if current_user.role == UserRole.ADMIN and payload.professional_note:
        raise HTTPException(status_code=403, detail="专业处理意见只能由心理老师填写")

    transitions = {
        ReferralStatus.PENDING: {ReferralStatus.ACCEPTED, ReferralStatus.REJECTED},
        ReferralStatus.ACCEPTED: {ReferralStatus.COMPLETED, ReferralStatus.REJECTED},
    }
    if payload.status != referral.status and payload.status not in transitions[referral.status]:
        raise HTTPException(status_code=422, detail="不允许的转介状态流转")

    assignee_id = payload.assigned_to_id
    if payload.status in {ReferralStatus.ACCEPTED, ReferralStatus.COMPLETED}:
        if current_user.role == UserRole.PSYCHOLOGIST and assignee_id is None:
            assignee_id = current_user.id
        assignee = ensure_user_exists(db, assignee_id, role=UserRole.PSYCHOLOGIST)
        assert assignee is not None
        if current_user.role == UserRole.PSYCHOLOGIST and assignee.id != current_user.id:
            raise HTTPException(status_code=403, detail="心理老师只能接收分配给自己的转介")
        referral.assigned_to_id = assignee.id
    elif assignee_id:
        assignee = ensure_user_exists(db, assignee_id, role=UserRole.PSYCHOLOGIST)
        referral.assigned_to_id = assignee.id if assignee else None

    if payload.status == ReferralStatus.COMPLETED and not payload.professional_note:
        raise HTTPException(status_code=422, detail="完成转介时必须填写专业处理意见")
    referral.status = payload.status
    if payload.professional_note is not None:
        referral.professional_note = payload.professional_note.strip()
    if payload.status in {ReferralStatus.COMPLETED, ReferralStatus.REJECTED}:
        referral.processed_at = utcnow()
        referral.case.status = (
            CaseStatus.MONITORING if payload.status == ReferralStatus.COMPLETED else CaseStatus.OPEN
        )

    add_audit_log(
        db,
        actor=current_user,
        action="UPDATE_REFERRAL",
        resource_type="REFERRAL",
        resource_id=referral.id,
        summary=f"将转介状态更新为 {payload.status.value}",
        request=request,
    )
    db.commit()
    item = db.scalar(_list_statement(current_user).where(Referral.id == referral.id))
    return _safe_referral(item, current_user)
