from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db, utcnow
from app.dependencies import get_current_user
from app.models import User
from app.schemas import ChangePasswordRequest, LoginRequest, MessageResponse, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.serializers import user_out

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(User.username == payload.username).options(joinedload(User.organization))
    )
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    user.last_login_at = utcnow()
    add_audit_log(
        db,
        actor=user,
        action="LOGIN",
        resource_type="USER",
        resource_id=user.id,
        summary=f"{user.full_name} 登录系统",
        request=request,
    )
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user=user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return user_out(current_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    current_user.password_hash = hash_password(payload.new_password)
    add_audit_log(
        db,
        actor=current_user,
        action="CHANGE_PASSWORD",
        resource_type="USER",
        resource_id=current_user.id,
        summary=f"{current_user.full_name} 修改登录密码",
        request=request,
    )
    db.commit()
    return MessageResponse(message="密码已修改")
