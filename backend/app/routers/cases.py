from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db, utcnow
from app.dependencies import get_current_user
from app.enums import CaseStatus, Confidentiality, FollowUpStatus, RiskLevel, UserRole
from app.models import CareCase, FollowUp, RiskChange, Student, User
from app.permissions import (
    case_scope_condition,
    ensure_case_access,
    ensure_case_modify,
    ensure_student_access,
    ensure_user_exists,
)
from app.schemas import (
    CaseCreate,
    CaseDetail,
    CaseListItem,
    CaseUpdate,
    CloseCaseRequest,
    Page,
    RiskChangeCreate,
)
from app.serializers import case_detail_out, case_list_item
from app.services.case_service import (
    active_case_for_student,
    change_risk,
    generate_case_no,
    get_case_detail,
    recalculate_next_follow_up,
)

router = APIRouter(prefix="/cases", tags=["关怀个案"])


def _list_statement():
    return (
        select(CareCase)
        .join(CareCase.student)
        .options(
            joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(CareCase.student).joinedload(Student.counselor),
            joinedload(CareCase.owner),
        )
    )


def _validate_owner(db: Session, owner_id: int) -> User:
    owner = ensure_user_exists(db, owner_id)
    assert owner is not None
    if owner.role not in {UserRole.COUNSELOR, UserRole.PSYCHOLOGIST}:
        raise HTTPException(status_code=422, detail="个案负责人必须是辅导员或心理老师")
    return owner


@router.get("", response_model=Page[CaseListItem])
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    risk_level: RiskLevel | None = None,
    status: CaseStatus | None = None,
    organization_id: int | None = None,
    owner_id: int | None = None,
    overdue: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = _list_statement().where(case_scope_condition(current_user))
    count_stmt = (
        select(func.count(CareCase.id))
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
    )
    conditions = []
    if keyword:
        conditions.append(
            or_(
                CareCase.case_no.contains(keyword),
                Student.student_no.contains(keyword),
                Student.name.contains(keyword),
            )
        )
    if risk_level:
        conditions.append(CareCase.risk_level == risk_level)
    if status:
        conditions.append(CareCase.status == status)
    if organization_id:
        conditions.append(Student.organization_id == organization_id)
    if owner_id:
        conditions.append(CareCase.owner_id == owner_id)
    if overdue is True:
        conditions.extend(
            [
                CareCase.status != CaseStatus.CLOSED,
                CareCase.next_follow_up_at.is_not(None),
                CareCase.next_follow_up_at < utcnow(),
            ]
        )
    elif overdue is False:
        conditions.append(
            or_(CareCase.next_follow_up_at.is_(None), CareCase.next_follow_up_at >= utcnow())
        )
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(CareCase.risk_level.desc(), CareCase.next_follow_up_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page(
        items=[case_list_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(
    payload: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {
        UserRole.ADMIN,
        UserRole.COUNSELOR,
        UserRole.PSYCHOLOGIST,
    }:
        raise HTTPException(status_code=403, detail="没有创建个案的权限")
    student = db.scalar(
        select(Student)
        .where(Student.id == payload.student_id)
        .options(joinedload(Student.organization), joinedload(Student.counselor))
    )
    student = ensure_student_access(student, current_user)
    if active_case_for_student(db, student.id):
        raise HTTPException(status_code=409, detail="该学生已有未结案的关怀个案")

    owner_id = payload.owner_id
    if current_user.role in {UserRole.COUNSELOR, UserRole.PSYCHOLOGIST}:
        if owner_id not in {None, current_user.id}:
            raise HTTPException(status_code=403, detail="只能将新个案分配给自己")
        owner_id = current_user.id
    elif owner_id is None:
        owner_id = student.counselor_id
    if owner_id is None:
        raise HTTPException(status_code=422, detail="必须指定个案负责人")
    owner = _validate_owner(db, owner_id)
    if owner.role == UserRole.COUNSELOR and owner.organization_id != student.organization_id:
        raise HTTPException(status_code=422, detail="负责人和学生所属机构不一致")

    case = CareCase(
        case_no=generate_case_no(db),
        student_id=student.id,
        owner_id=owner.id,
        risk_level=payload.risk_level,
        status=CaseStatus.OPEN,
        source=payload.source.strip(),
        issue_tags=payload.issue_tags,
        summary=payload.summary.strip(),
        confidentiality=payload.confidentiality,
        next_follow_up_at=payload.next_follow_up_at,
    )
    db.add(case)
    db.flush()
    db.add(
        RiskChange(
            case_id=case.id,
            from_level=None,
            to_level=case.risk_level,
            reason="建立关怀个案时确定初始风险等级",
            changed_by_id=current_user.id,
        )
    )
    if payload.next_follow_up_at:
        db.add(
            FollowUp(
                case_id=case.id,
                created_by_id=current_user.id,
                scheduled_at=payload.next_follow_up_at,
                status=FollowUpStatus.PLANNED,
                summary="建档后首次随访",
            )
        )
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_CASE",
        resource_type="CARE_CASE",
        resource_id=case.id,
        summary=f"为 {student.name} 创建关怀个案 {case.case_no}",
        request=request,
        extra_data={"risk_level": case.risk_level.value},
    )
    db.commit()
    return case_detail_out(get_case_detail(db, case.id))


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = get_case_detail(db, case_id)
    case = ensure_case_access(case, current_user, include_sensitive=True)
    if case.confidentiality == Confidentiality.RESTRICTED:
        add_audit_log(
            db,
            actor=current_user,
            action="VIEW_RESTRICTED_CASE",
            resource_type="CARE_CASE",
            resource_id=case.id,
            summary=f"查看受限个案 {case.case_no}",
            request=request,
        )
        db.commit()
    return case_detail_out(case)


@router.patch("/{case_id}", response_model=CaseDetail)
def update_case(
    case_id: int,
    payload: CaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    values = payload.model_dump(exclude_unset=True)
    requested_status = values.get("status")
    if requested_status == CaseStatus.CLOSED:
        raise HTTPException(status_code=422, detail="请使用结案接口关闭个案")
    if requested_status == CaseStatus.REFERRED:
        raise HTTPException(status_code=422, detail="已转介状态只能由转介流程维护")
    if case.status == CaseStatus.REFERRED and requested_status is not None:
        raise HTTPException(status_code=409, detail="转介处理期间不能手工修改个案状态")
    if "owner_id" in values:
        owner_id = values.pop("owner_id")
        if owner_id is None:
            raise HTTPException(status_code=422, detail="个案负责人不能为空")
        owner = _validate_owner(db, owner_id)
        if (
            owner.role == UserRole.COUNSELOR
            and owner.organization_id != case.student.organization_id
        ):
            raise HTTPException(status_code=422, detail="负责人和学生所属机构不一致")
        if current_user.role == UserRole.COUNSELOR and owner.id != current_user.id:
            raise HTTPException(status_code=403, detail="辅导员不能转派给其他人员")
        case.owner_id = owner.id
    for field, value in values.items():
        setattr(case, field, value.strip() if isinstance(value, str) else value)
    add_audit_log(
        db,
        actor=current_user,
        action="UPDATE_CASE",
        resource_type="CARE_CASE",
        resource_id=case.id,
        summary=f"更新关怀个案 {case.case_no}",
        request=request,
    )
    db.commit()
    return case_detail_out(get_case_detail(db, case.id))


@router.post("/{case_id}/risk", response_model=CaseDetail)
def update_risk(
    case_id: int,
    payload: RiskChangeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    previous = case.risk_level
    change = change_risk(
        db,
        case,
        risk_level=payload.risk_level,
        reason=payload.reason,
        changed_by_id=current_user.id,
    )
    if change is None:
        raise HTTPException(status_code=409, detail="风险等级没有变化")
    add_audit_log(
        db,
        actor=current_user,
        action="CHANGE_RISK",
        resource_type="CARE_CASE",
        resource_id=case.id,
        summary=f"个案 {case.case_no} 风险等级由 {previous.value} 调整为 {payload.risk_level.value}",
        request=request,
    )
    db.commit()
    return case_detail_out(get_case_detail(db, case.id))


@router.post("/{case_id}/close", response_model=CaseDetail)
def close_case(
    case_id: int,
    payload: CloseCaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = ensure_case_modify(get_case_detail(db, case_id), current_user)
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=409, detail="个案已经结案")
    if case.risk_level == RiskLevel.RED and current_user.role != UserRole.PSYCHOLOGIST:
        raise HTTPException(status_code=403, detail="红色风险个案只能由心理老师结案")
    case.status = CaseStatus.CLOSED
    case.closed_at = utcnow()
    case.close_reason = payload.reason.strip()
    case.next_follow_up_at = None
    db.query(FollowUp).filter(
        FollowUp.case_id == case.id, FollowUp.status == FollowUpStatus.PLANNED
    ).update({FollowUp.status: FollowUpStatus.CANCELLED}, synchronize_session=False)
    recalculate_next_follow_up(db, case)
    add_audit_log(
        db,
        actor=current_user,
        action="CLOSE_CASE",
        resource_type="CARE_CASE",
        resource_id=case.id,
        summary=f"结案 {case.case_no}：{payload.reason[:100]}",
        request=request,
    )
    db.commit()
    return case_detail_out(get_case_detail(db, case.id))
