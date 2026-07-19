from collections import Counter
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import utcnow
from app.enums import CaseStatus, FollowUpStatus, RiskLevel
from app.models import CareCase, FollowUp, Student, User
from app.permissions import case_scope_condition
from app.schemas import DistributionItem, MonthlyCount, ReportSummary
from app.time_utils import as_local_date, date_range_bounds_utc

RISK_LABELS = {
    RiskLevel.GREEN.value: "一般关注",
    RiskLevel.YELLOW.value: "重点关注",
    RiskLevel.RED.value: "紧急关注",
}
STATUS_LABELS = {
    CaseStatus.OPEN.value: "跟进中",
    CaseStatus.MONITORING.value: "稳定观察",
    CaseStatus.REFERRED.value: "已转介",
    CaseStatus.CLOSED.value: "已结案",
}


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _distribution(counter: Counter[str], labels: dict[str, str] | None = None):
    labels = labels or {}
    return [
        DistributionItem(key=key, label=labels.get(key, key), count=count)
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_report(
    db: Session,
    *,
    current_user: User,
    date_from: date,
    date_to: date,
    organization_id: int | None = None,
) -> ReportSummary:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    if (date_to - date_from).days > 366:
        raise HTTPException(status_code=422, detail="单次报表时间范围不能超过 366 天")

    start_at, end_at = date_range_bounds_utc(date_from, date_to)
    case_stmt = (
        select(CareCase)
        .join(CareCase.student)
        .where(case_scope_condition(current_user))
        .options(
            joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(CareCase.owner),
        )
    )
    if organization_id:
        case_stmt = case_stmt.where(Student.organization_id == organization_id)
    cases = list(db.scalars(case_stmt).unique())
    case_ids = [item.id for item in cases]

    active_cases = [item for item in cases if item.status != CaseStatus.CLOSED]
    new_cases = [item for item in cases if start_at <= _as_utc(item.opened_at) < end_at]
    closed_cases = [
        item for item in cases if item.closed_at and start_at <= _as_utc(item.closed_at) < end_at
    ]

    followups: list[FollowUp] = []
    overdue_tasks: list[FollowUp] = []
    if case_ids:
        followups = list(
            db.scalars(
                select(FollowUp).where(
                    FollowUp.case_id.in_(case_ids),
                    FollowUp.completed_at.is_not(None),
                    FollowUp.completed_at >= start_at,
                    FollowUp.completed_at < end_at,
                    FollowUp.status.in_([FollowUpStatus.COMPLETED, FollowUpStatus.UNREACHABLE]),
                )
            )
        )
        overdue_tasks = list(
            db.scalars(
                select(FollowUp).where(
                    FollowUp.case_id.in_(case_ids),
                    FollowUp.status == FollowUpStatus.PLANNED,
                    FollowUp.scheduled_at < utcnow(),
                )
            )
        )

    on_time = 0
    for item in followups:
        if item.completed_at and as_local_date(item.completed_at) <= as_local_date(
            item.scheduled_at
        ):
            on_time += 1
    on_time_rate = round(on_time / len(followups) * 100, 1) if followups else 0.0

    risk_counter = Counter(item.risk_level.value for item in active_cases)
    status_counter = Counter(item.status.value for item in cases)
    issue_counter: Counter[str] = Counter()
    organization_counter: Counter[str] = Counter()
    for item in active_cases:
        issue_counter.update(item.issue_tags or ["未分类"])
        organization_counter[item.student.organization.name] += 1

    monthly_counter: Counter[str] = Counter()
    for item in followups:
        if item.completed_at:
            monthly_counter[as_local_date(item.completed_at).strftime("%Y-%m")] += 1

    return ReportSummary(
        date_from=date_from,
        date_to=date_to,
        active_case_count=len(active_cases),
        new_case_count=len(new_cases),
        closed_case_count=len(closed_cases),
        completed_followup_count=len(followups),
        overdue_task_count=len(overdue_tasks),
        on_time_rate=on_time_rate,
        risk_distribution=_distribution(risk_counter, RISK_LABELS),
        status_distribution=_distribution(status_counter, STATUS_LABELS),
        issue_distribution=_distribution(issue_counter),
        organization_distribution=_distribution(organization_counter),
        monthly_followups=[
            MonthlyCount(month=month, count=count)
            for month, count in sorted(monthly_counter.items())
        ],
    )
