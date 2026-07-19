from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends

from app.database import get_db, utcnow
from app.dependencies import get_current_user
from app.enums import CaseStatus, FollowUpStatus, ReferralStatus, RiskLevel
from app.models import CareCase, FollowUp, Referral, User
from app.permissions import case_scope_condition
from app.schemas import DashboardOut, DashboardTask
from app.serializers import is_overdue
from app.time_utils import day_bounds_utc, local_today, month_bounds_utc

router = APIRouter(prefix="/dashboard", tags=["工作台"])


@router.get("", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = case_scope_condition(current_user)
    case_base = select(func.count(CareCase.id)).join(CareCase.student).where(access)
    active_cases = db.scalar(case_base.where(CareCase.status != CaseStatus.CLOSED)) or 0
    red_cases = (
        db.scalar(
            case_base.where(
                CareCase.status != CaseStatus.CLOSED,
                CareCase.risk_level == RiskLevel.RED,
            )
        )
        or 0
    )

    today_start, today_end = day_bounds_utc(local_today())
    month_start, month_end = month_bounds_utc(local_today())
    followup_base = (
        select(func.count(FollowUp.id)).join(FollowUp.case).join(CareCase.student).where(access)
    )
    due_today = (
        db.scalar(
            followup_base.where(
                FollowUp.status == FollowUpStatus.PLANNED,
                FollowUp.scheduled_at >= today_start,
                FollowUp.scheduled_at < today_end,
            )
        )
        or 0
    )
    overdue_tasks = (
        db.scalar(
            followup_base.where(
                FollowUp.status == FollowUpStatus.PLANNED,
                FollowUp.scheduled_at < utcnow(),
            )
        )
        or 0
    )
    completed_this_month = (
        db.scalar(
            followup_base.where(
                FollowUp.status.in_([FollowUpStatus.COMPLETED, FollowUpStatus.UNREACHABLE]),
                FollowUp.completed_at >= month_start,
                FollowUp.completed_at < month_end,
            )
        )
        or 0
    )
    pending_referrals = (
        db.scalar(
            select(func.count(Referral.id))
            .join(Referral.case)
            .join(CareCase.student)
            .where(
                access,
                Referral.status.in_([ReferralStatus.PENDING, ReferralStatus.ACCEPTED]),
            )
        )
        or 0
    )

    tasks = list(
        db.scalars(
            select(FollowUp)
            .join(FollowUp.case)
            .join(CareCase.student)
            .where(access, FollowUp.status == FollowUpStatus.PLANNED)
            .options(
                joinedload(FollowUp.case).joinedload(CareCase.student),
            )
            .order_by(FollowUp.scheduled_at.asc())
            .limit(20)
        ).unique()
    )
    return DashboardOut(
        active_cases=active_cases,
        red_cases=red_cases,
        due_today=due_today,
        overdue_tasks=overdue_tasks,
        completed_this_month=completed_this_month,
        pending_referrals=pending_referrals,
        tasks=[
            DashboardTask(
                followup_id=item.id,
                case_id=item.case_id,
                student_id=item.case.student_id,
                student_name=item.case.student.name,
                student_no=item.case.student.student_no,
                risk_level=item.case.risk_level,
                scheduled_at=item.scheduled_at,
                is_overdue=is_overdue(item.scheduled_at),
            )
            for item in tasks
        ],
    )
