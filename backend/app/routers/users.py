from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.enums import CaseStatus, UserRole
from app.models import CareCase, Organization, Student, User
from app.permissions import ensure_user_exists
from app.schemas import Page, UserCreate, UserOption, UserOut, UserUpdate
from app.security import hash_password
from app.serializers import user_out

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/options", response_model=list[UserOption])
def user_options(
    role: UserRole | None = None,
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(User).where(User.is_active.is_(True)).order_by(User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    if organization_id:
        stmt = stmt.where(User.organization_id == organization_id)
    return [
        UserOption(
            id=item.id,
            full_name=item.full_name,
            username=item.username,
            role=item.role,
            organization_id=item.organization_id,
        )
        for item in db.scalars(stmt)
    ]


@router.get("", response_model=Page[UserOut])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    stmt = select(User).options(joinedload(User.organization))
    count_stmt = select(func.count(User.id))
    if keyword:
        condition = User.username.contains(keyword) | User.full_name.contains(keyword)
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    total = db.scalar(count_stmt) or 0
    users = db.scalars(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique()
    return Page(
        items=[user_out(item) for item in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    if payload.role == UserRole.COUNSELOR and payload.organization_id is None:
        raise HTTPException(status_code=422, detail="辅导员必须绑定所属机构")
    if payload.organization_id is not None:
        organization = db.get(Organization, payload.organization_id)
        if organization is None or not organization.is_active:
            raise HTTPException(status_code=422, detail="指定机构不存在或已停用")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        organization_id=payload.organization_id,
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在") from None
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_USER",
        resource_type="USER",
        resource_id=user.id,
        summary=f"创建用户：{user.full_name}（{user.username}）",
        request=request,
    )
    db.commit()
    user = db.scalar(select(User).where(User.id == user.id).options(joinedload(User.organization)))
    return user_out(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = ensure_user_exists(db, user_id)
    assert user is not None
    values = payload.model_dump(exclude_unset=True)
    if user.id == current_user.id:
        if values.get("is_active") is False:
            raise HTTPException(status_code=400, detail="不能停用当前登录账号")
        if "role" in values and values["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=400, detail="不能移除当前账号的管理员角色")
    target_role = values.get("role", user.role)
    target_organization_id = values.get("organization_id", user.organization_id)
    if target_role == UserRole.COUNSELOR and target_organization_id is None:
        raise HTTPException(status_code=422, detail="辅导员必须绑定所属机构")
    if "organization_id" in values and values["organization_id"] is not None:
        organization = db.get(Organization, values["organization_id"])
        if organization is None or not organization.is_active:
            raise HTTPException(status_code=422, detail="指定机构不存在或已停用")

    has_active_cases = (
        db.scalar(
            select(func.count(CareCase.id)).where(
                CareCase.owner_id == user.id, CareCase.status != CaseStatus.CLOSED
            )
        )
        or 0
    ) > 0
    has_active_students = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.counselor_id == user.id, Student.is_active.is_(True)
            )
        )
        or 0
    ) > 0
    if values.get("is_active") is False and (has_active_cases or has_active_students):
        raise HTTPException(
            status_code=409,
            detail="该用户仍负责在管个案或在校学生，请先完成转派再停用",
        )
    if "role" in values and values["role"] != user.role and has_active_cases:
        raise HTTPException(status_code=409, detail="该用户仍负责在管个案，请先完成转派再修改角色")
    if (
        "organization_id" in values
        and values["organization_id"] != user.organization_id
        and has_active_students
    ):
        raise HTTPException(
            status_code=409, detail="该辅导员仍负责在校学生，请先完成转派再更换机构"
        )

    password = values.pop("password", None)
    for field, value in values.items():
        setattr(user, field, value)
    if password:
        user.password_hash = hash_password(password)
    add_audit_log(
        db,
        actor=current_user,
        action="UPDATE_USER",
        resource_type="USER",
        resource_id=user.id,
        summary=f"更新用户：{user.full_name}",
        request=request,
    )
    db.commit()
    user = db.scalar(select(User).where(User.id == user.id).options(joinedload(User.organization)))
    return user_out(user)
