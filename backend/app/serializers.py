from datetime import datetime, timezone

from app.enums import CaseStatus, FollowUpStatus
from app.models import AuditLog, CareCase, FollowUp, Referral, RiskChange, Student, User
from app.schemas import (
    AuditLogOut,
    CaseDetail,
    CaseListItem,
    FollowUpOut,
    ReferralOut,
    RiskChangeOut,
    StudentOut,
    UserOut,
)


def _now_for(value: datetime | None) -> datetime:
    if value is not None and value.tzinfo is None:
        return datetime.now()
    return datetime.now(timezone.utc)


def is_overdue(value: datetime | None, *, active: bool = True) -> bool:
    return bool(value and active and value < _now_for(value))


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=user.organization.name if user.organization else None,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def case_list_item(case: CareCase) -> CaseListItem:
    return CaseListItem(
        id=case.id,
        case_no=case.case_no,
        student_id=case.student_id,
        student_no=case.student.student_no,
        student_name=case.student.name,
        organization_name=case.student.organization.name,
        owner_id=case.owner_id,
        owner_name=case.owner.full_name,
        risk_level=case.risk_level,
        status=case.status,
        source=case.source,
        issue_tags=case.issue_tags or [],
        confidentiality=case.confidentiality,
        next_follow_up_at=case.next_follow_up_at,
        opened_at=case.opened_at,
        is_overdue=is_overdue(case.next_follow_up_at, active=case.status != CaseStatus.CLOSED),
    )


def student_out(student: Student, active_case: CareCase | None = None) -> StudentOut:
    return StudentOut(
        id=student.id,
        student_no=student.student_no,
        name=student.name,
        gender=student.gender,
        organization_id=student.organization_id,
        organization_name=student.organization.name,
        major=student.major,
        grade=student.grade,
        class_name=student.class_name,
        phone=student.phone,
        emergency_contact_name=student.emergency_contact_name,
        emergency_contact_phone=student.emergency_contact_phone,
        counselor_id=student.counselor_id,
        counselor_name=student.counselor.full_name if student.counselor else None,
        is_active=student.is_active,
        active_case=case_list_item(active_case) if active_case else None,
        created_at=student.created_at,
    )


def followup_out(item: FollowUp) -> FollowUpOut:
    return FollowUpOut(
        id=item.id,
        case_id=item.case_id,
        case_no=item.case.case_no,
        student_id=item.case.student_id,
        student_no=item.case.student.student_no,
        student_name=item.case.student.name,
        created_by_id=item.created_by_id,
        created_by_name=item.created_by.full_name,
        scheduled_at=item.scheduled_at,
        completed_at=item.completed_at,
        status=item.status,
        method=item.method,
        condition=item.condition,
        issue_tags=item.issue_tags or [],
        summary=item.summary,
        actions=item.actions,
        contact_result=item.contact_result,
        next_follow_up_at=item.next_follow_up_at,
        is_overdue=is_overdue(item.scheduled_at, active=item.status == FollowUpStatus.PLANNED),
        created_at=item.created_at,
    )


def risk_change_out(item: RiskChange) -> RiskChangeOut:
    return RiskChangeOut(
        id=item.id,
        from_level=item.from_level,
        to_level=item.to_level,
        reason=item.reason,
        changed_by_id=item.changed_by_id,
        changed_by_name=item.changed_by.full_name,
        created_at=item.created_at,
    )


def referral_out(item: Referral) -> ReferralOut:
    return ReferralOut(
        id=item.id,
        case_id=item.case_id,
        case_no=item.case.case_no,
        student_id=item.case.student_id,
        student_no=item.case.student.student_no,
        student_name=item.case.student.name,
        requested_by_id=item.requested_by_id,
        requested_by_name=item.requested_by.full_name,
        assigned_to_id=item.assigned_to_id,
        assigned_to_name=item.assigned_to.full_name if item.assigned_to else None,
        status=item.status,
        reason=item.reason,
        professional_note=item.professional_note,
        created_at=item.created_at,
        processed_at=item.processed_at,
    )


def audit_log_out(item: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=item.id,
        actor_id=item.actor_id,
        actor_name=item.actor.full_name if item.actor else None,
        action=item.action,
        resource_type=item.resource_type,
        resource_id=item.resource_id,
        summary=item.summary,
        ip_address=item.ip_address,
        extra_data=item.extra_data or {},
        created_at=item.created_at,
    )


def case_detail_out(case: CareCase) -> CaseDetail:
    base = case_list_item(case).model_dump()
    return CaseDetail(
        **base,
        summary=case.summary,
        student=student_out(case.student, case if case.status != CaseStatus.CLOSED else None),
        followups=[followup_out(item) for item in case.followups],
        risk_history=[risk_change_out(item) for item in case.risk_history],
        referrals=[referral_out(item) for item in case.referrals],
        closed_at=case.closed_at,
        close_reason=case.close_reason,
    )
