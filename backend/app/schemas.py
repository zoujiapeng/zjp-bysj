from datetime import date, datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
from app.time_utils import local_timezone

T = TypeVar("T")


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=local_timezone())
    return value.astimezone(timezone.utc)


def clean_tag_list(value: list[str]) -> list[str]:
    result: list[str] = []
    for item in value:
        normalized = item.strip()
        if normalized and normalized not in result:
            result.append(normalized[:50])
    return result


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class OrganizationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=100)


class OrganizationUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=100)
    role: UserRole
    organization_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    role: UserRole | None = None
    organization_id: int | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    organization_id: int | None
    organization_name: str | None = None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserOption(BaseModel):
    id: int
    full_name: str
    username: str
    role: UserRole
    organization_id: int | None


class StudentCreate(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=20)
    organization_id: int
    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=32)
    class_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    counselor_id: int | None = None


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=20)
    organization_id: int | None = None
    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=32)
    class_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    counselor_id: int | None = None
    is_active: bool | None = None


class StudentOut(BaseModel):
    id: int
    student_no: str
    name: str
    gender: str | None
    organization_id: int
    organization_name: str
    major: str | None
    grade: str | None
    class_name: str | None
    phone: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    counselor_id: int | None
    counselor_name: str | None
    is_active: bool
    active_case: "CaseListItem | None" = None
    created_at: datetime


class CaseCreate(BaseModel):
    student_id: int
    owner_id: int | None = None
    risk_level: RiskLevel = RiskLevel.GREEN
    source: str = Field(min_length=1, max_length=100)
    issue_tags: list[str] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1, max_length=5000)
    confidentiality: Confidentiality = Confidentiality.NORMAL
    next_follow_up_at: datetime | None = None

    @field_validator("issue_tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return clean_tag_list(value)

    @field_validator("next_follow_up_at")
    @classmethod
    def normalize_next_follow_up(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)


class CaseUpdate(BaseModel):
    owner_id: int | None = None
    source: str | None = Field(default=None, min_length=1, max_length=100)
    issue_tags: list[str] | None = Field(default=None, max_length=20)
    summary: str | None = Field(default=None, min_length=1, max_length=5000)
    confidentiality: Confidentiality | None = None
    status: CaseStatus | None = None

    @field_validator("issue_tags")
    @classmethod
    def clean_optional_tags(cls, value: list[str] | None) -> list[str] | None:
        return clean_tag_list(value) if value is not None else None


class RiskChangeCreate(BaseModel):
    risk_level: RiskLevel
    reason: str = Field(min_length=2, max_length=2000)


class CloseCaseRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)


class CaseListItem(BaseModel):
    id: int
    case_no: str
    student_id: int
    student_no: str
    student_name: str
    organization_name: str
    owner_id: int
    owner_name: str
    risk_level: RiskLevel
    status: CaseStatus
    source: str
    issue_tags: list[str]
    confidentiality: Confidentiality
    next_follow_up_at: datetime | None
    opened_at: datetime
    is_overdue: bool


class FollowUpPlanCreate(BaseModel):
    scheduled_at: datetime
    method: FollowUpMethod | None = None
    purpose: str | None = Field(default=None, max_length=1000)

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime) -> datetime:
        result = normalize_datetime(value)
        assert result is not None
        return result


class FollowUpCompleteCreate(BaseModel):
    method: FollowUpMethod
    condition: StudentCondition
    status: FollowUpStatus = FollowUpStatus.COMPLETED
    issue_tags: list[str] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1, max_length=5000)
    actions: str = Field(min_length=1, max_length=5000)
    contact_result: str | None = Field(default=None, max_length=200)
    completed_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    next_method: FollowUpMethod | None = None
    risk_level: RiskLevel | None = None
    risk_reason: str | None = Field(default=None, max_length=2000)

    @field_validator("completed_at", "next_follow_up_at")
    @classmethod
    def normalize_followup_datetimes(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)

    @field_validator("issue_tags")
    @classmethod
    def clean_followup_tags(cls, value: list[str]) -> list[str]:
        return clean_tag_list(value)

    @field_validator("status")
    @classmethod
    def status_must_be_result(cls, value: FollowUpStatus) -> FollowUpStatus:
        if value not in {FollowUpStatus.COMPLETED, FollowUpStatus.UNREACHABLE}:
            raise ValueError("完成随访时状态只能为 COMPLETED 或 UNREACHABLE")
        return value


class FollowUpOut(BaseModel):
    id: int
    case_id: int
    case_no: str
    student_id: int
    student_no: str
    student_name: str
    created_by_id: int
    created_by_name: str
    scheduled_at: datetime
    completed_at: datetime | None
    status: FollowUpStatus
    method: FollowUpMethod | None
    condition: StudentCondition
    issue_tags: list[str]
    summary: str | None
    actions: str | None
    contact_result: str | None
    next_follow_up_at: datetime | None
    is_overdue: bool
    created_at: datetime


class RiskChangeOut(BaseModel):
    id: int
    from_level: RiskLevel | None
    to_level: RiskLevel
    reason: str
    changed_by_id: int
    changed_by_name: str
    created_at: datetime


class ReferralCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=5000)
    assigned_to_id: int | None = None


class ReferralUpdate(BaseModel):
    status: ReferralStatus
    assigned_to_id: int | None = None
    professional_note: str | None = Field(default=None, max_length=5000)


class ReferralOut(BaseModel):
    id: int
    case_id: int
    case_no: str
    student_id: int
    student_no: str
    student_name: str
    requested_by_id: int
    requested_by_name: str
    assigned_to_id: int | None
    assigned_to_name: str | None
    status: ReferralStatus
    reason: str
    professional_note: str | None
    created_at: datetime
    processed_at: datetime | None


class CaseDetail(CaseListItem):
    summary: str
    student: StudentOut
    followups: list[FollowUpOut]
    risk_history: list[RiskChangeOut]
    referrals: list[ReferralOut]
    closed_at: datetime | None
    close_reason: str | None


class DashboardTask(BaseModel):
    followup_id: int
    case_id: int
    student_id: int
    student_name: str
    student_no: str
    risk_level: RiskLevel
    scheduled_at: datetime
    is_overdue: bool


class DashboardOut(BaseModel):
    active_cases: int
    red_cases: int
    due_today: int
    overdue_tasks: int
    completed_this_month: int
    pending_referrals: int
    tasks: list[DashboardTask]


class DistributionItem(BaseModel):
    key: str
    label: str
    count: int


class MonthlyCount(BaseModel):
    month: str
    count: int


class ReportSummary(BaseModel):
    date_from: date
    date_to: date
    active_case_count: int
    new_case_count: int
    closed_case_count: int
    completed_followup_count: int
    overdue_task_count: int
    on_time_rate: float
    risk_distribution: list[DistributionItem]
    status_distribution: list[DistributionItem]
    issue_distribution: list[DistributionItem]
    organization_distribution: list[DistributionItem]
    monthly_followups: list[MonthlyCount]


class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None
    actor_name: str | None
    action: str
    resource_type: str
    resource_id: str | None
    summary: str
    ip_address: str | None
    extra_data: dict[str, object]
    created_at: datetime


class ImportErrorItem(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[ImportErrorItem]


class MessageResponse(BaseModel):
    message: str


TokenResponse.model_rebuild()
StudentOut.model_rebuild()
CaseDetail.model_rebuild()
