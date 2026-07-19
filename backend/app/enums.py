from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    COUNSELOR = "COUNSELOR"
    PSYCHOLOGIST = "PSYCHOLOGIST"


class RiskLevel(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    MONITORING = "MONITORING"
    REFERRED = "REFERRED"
    CLOSED = "CLOSED"


class Confidentiality(StrEnum):
    NORMAL = "NORMAL"
    RESTRICTED = "RESTRICTED"


class FollowUpStatus(StrEnum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    UNREACHABLE = "UNREACHABLE"
    CANCELLED = "CANCELLED"


class FollowUpMethod(StrEnum):
    IN_PERSON = "IN_PERSON"
    PHONE = "PHONE"
    MESSAGE = "MESSAGE"
    HOME_VISIT = "HOME_VISIT"
    OTHER = "OTHER"


class StudentCondition(StrEnum):
    IMPROVED = "IMPROVED"
    STABLE = "STABLE"
    WORSE = "WORSE"
    UNKNOWN = "UNKNOWN"


class ReferralStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
