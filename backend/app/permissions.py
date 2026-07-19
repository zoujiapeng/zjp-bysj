from fastapi import HTTPException
from sqlalchemy import Select, or_, true
from sqlalchemy.orm import Session

from app.enums import Confidentiality, UserRole
from app.models import CareCase, Student, User


def student_scope(stmt: Select, user: User) -> Select:
    if user.role in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        return stmt
    if user.organization_id is None:
        return stmt.where(Student.id == -1)
    return stmt.where(Student.organization_id == user.organization_id)


def case_scope(stmt: Select, user: User) -> Select:
    if user.role in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        return stmt
    return stmt.join(CareCase.student).where(
        or_(CareCase.owner_id == user.id, Student.counselor_id == user.id)
    )


def case_scope_condition(user: User):
    if user.role in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        return true()
    return or_(CareCase.owner_id == user.id, Student.counselor_id == user.id)


def ensure_student_access(student: Student | None, user: User) -> Student:
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    if user.role in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        return student
    if user.organization_id is not None and student.organization_id == user.organization_id:
        return student
    raise HTTPException(status_code=403, detail="无权查看该学生")


def ensure_case_access(
    case: CareCase | None,
    user: User,
    *,
    include_sensitive: bool = True,
) -> CareCase:
    if case is None:
        raise HTTPException(status_code=404, detail="关怀个案不存在")

    if user.role == UserRole.PSYCHOLOGIST:
        return case

    if user.role == UserRole.ADMIN:
        if include_sensitive and case.confidentiality == Confidentiality.RESTRICTED:
            raise HTTPException(status_code=403, detail="受限个案仅负责人和心理老师可查看")
        return case

    if case.owner_id == user.id or case.student.counselor_id == user.id:
        return case
    raise HTTPException(status_code=403, detail="无权查看该关怀个案")


def ensure_case_modify(case: CareCase | None, user: User) -> CareCase:
    case = ensure_case_access(case, user, include_sensitive=True)
    if user.role in {UserRole.PSYCHOLOGIST, UserRole.ADMIN} or case.owner_id == user.id:
        return case
    raise HTTPException(status_code=403, detail="只有个案负责人或心理老师可以修改")


def ensure_user_exists(
    db: Session, user_id: int | None, *, role: UserRole | None = None
) -> User | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=422, detail="指定用户不存在或已停用")
    if role is not None and user.role != role:
        raise HTTPException(status_code=422, detail=f"指定用户角色必须为 {role.value}")
    return user
