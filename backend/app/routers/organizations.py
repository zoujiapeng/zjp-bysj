from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import add_audit_log
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.enums import UserRole
from app.models import Organization, Student, User
from app.schemas import OrganizationCreate, OrganizationOut, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["组织机构"])


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Organization).order_by(Organization.name)
    if not include_inactive:
        stmt = stmt.where(Organization.is_active.is_(True))
    return list(db.scalars(stmt))


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization = Organization(code=payload.code.strip(), name=payload.name.strip())
    db.add(organization)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="机构编码或名称已存在") from None
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_ORGANIZATION",
        resource_type="ORGANIZATION",
        resource_id=organization.id,
        summary=f"创建机构：{organization.name}",
        request=request,
    )
    db.commit()
    db.refresh(organization)
    return organization


@router.patch("/{organization_id}", response_model=OrganizationOut)
def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="机构不存在")
    values = payload.model_dump(exclude_unset=True)
    if values.get("is_active") is False and organization.is_active:
        active_users = (
            db.scalar(
                select(func.count(User.id)).where(
                    User.organization_id == organization.id, User.is_active.is_(True)
                )
            )
            or 0
        )
        active_students = (
            db.scalar(
                select(func.count(Student.id)).where(
                    Student.organization_id == organization.id, Student.is_active.is_(True)
                )
            )
            or 0
        )
        if active_users or active_students:
            raise HTTPException(
                status_code=409,
                detail="机构仍有关联的有效用户或在校学生，处理后才能停用",
            )
    for field, value in values.items():
        setattr(organization, field, value.strip() if isinstance(value, str) else value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="机构编码或名称已存在") from None
    add_audit_log(
        db,
        actor=current_user,
        action="UPDATE_ORGANIZATION",
        resource_type="ORGANIZATION",
        resource_id=organization.id,
        summary=f"更新机构：{organization.name}",
        request=request,
    )
    db.commit()
    db.refresh(organization)
    return organization
