import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db
from app.dependencies import get_current_user
from app.enums import CaseStatus
from app.models import CareCase, Student, User
from app.permissions import case_scope_condition
from app.schemas import ReportSummary
from app.services.report_service import build_report
from app.time_utils import local_today

router = APIRouter(prefix="/reports", tags=["报表"])


def _default_from() -> date:
    return local_today().replace(day=1)


@router.get("/summary", response_model=ReportSummary)
def report_summary(
    date_from: date = Query(default_factory=_default_from),
    date_to: date = Query(default_factory=local_today),
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_report(
        db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
    )


@router.get("/export.csv")
def export_report(
    request: Request,
    date_from: date = Query(default_factory=_default_from),
    date_to: date = Query(default_factory=local_today),
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = build_report(
        db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
    )
    stmt = (
        select(CareCase)
        .join(CareCase.student)
        .where(case_scope_condition(current_user), CareCase.status != CaseStatus.CLOSED)
        .options(
            joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(CareCase.owner),
        )
        .order_by(CareCase.risk_level.desc(), CareCase.next_follow_up_at.asc())
    )
    if organization_id:
        stmt = stmt.where(Student.organization_id == organization_id)
    cases = list(db.scalars(stmt).unique())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["学生心理关怀工作报表"])
    writer.writerow(["统计期间", str(date_from), str(date_to)])
    writer.writerow(["当前在管个案", summary.active_case_count])
    writer.writerow(["期间新增个案", summary.new_case_count])
    writer.writerow(["期间结案", summary.closed_case_count])
    writer.writerow(["已处理随访", summary.completed_followup_count])
    writer.writerow(["当前超期任务", summary.overdue_task_count])
    writer.writerow(["按时处理率", f"{summary.on_time_rate}%"])
    writer.writerow([])
    writer.writerow(
        [
            "个案编号",
            "学号",
            "姓名",
            "机构",
            "负责人",
            "风险等级",
            "个案状态",
            "问题标签",
            "下次随访时间",
        ]
    )
    for item in cases:
        writer.writerow(
            [
                item.case_no,
                item.student.student_no,
                item.student.name,
                item.student.organization.name,
                item.owner.full_name,
                item.risk_level.value,
                item.status.value,
                "、".join(item.issue_tags or []),
                item.next_follow_up_at.isoformat() if item.next_follow_up_at else "",
            ]
        )

    add_audit_log(
        db,
        actor=current_user,
        action="EXPORT_REPORT",
        resource_type="REPORT",
        resource_id=None,
        summary=f"导出 {date_from} 至 {date_to} 的关怀工作报表",
        request=request,
    )
    db.commit()
    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="care-report-{date_from}-{date_to}.csv"'
        },
    )
