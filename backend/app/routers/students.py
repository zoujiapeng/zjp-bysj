import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.audit import add_audit_log
from app.database import get_db
from app.dependencies import get_current_user
from app.enums import CaseStatus, UserRole
from app.models import CareCase, Organization, Student, User
from app.permissions import ensure_student_access, ensure_user_exists, student_scope
from app.schemas import (
    ImportErrorItem,
    ImportResult,
    Page,
    StudentCreate,
    StudentOut,
    StudentUpdate,
)
from app.serializers import student_out

router = APIRouter(prefix="/students", tags=["学生"])


def _student_statement():
    return select(Student).options(joinedload(Student.organization), joinedload(Student.counselor))


def _active_cases(db: Session, student_ids: list[int]) -> dict[int, CareCase]:
    if not student_ids:
        return {}
    items = db.scalars(
        select(CareCase)
        .where(CareCase.student_id.in_(student_ids), CareCase.status != CaseStatus.CLOSED)
        .options(
            joinedload(CareCase.student).joinedload(Student.organization),
            joinedload(CareCase.owner),
        )
        .order_by(CareCase.opened_at.desc())
    ).unique()
    result: dict[int, CareCase] = {}
    for item in items:
        result.setdefault(item.student_id, item)
    return result


def _validate_student_assignment(
    db: Session,
    current_user: User,
    organization_id: int,
    counselor_id: int | None,
) -> tuple[Organization, int | None]:
    organization = db.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=422, detail="指定机构不存在或已停用")

    if current_user.role == UserRole.COUNSELOR:
        if current_user.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="辅导员只能管理本机构学生")
        return organization, current_user.id

    if counselor_id is not None:
        counselor = ensure_user_exists(db, counselor_id, role=UserRole.COUNSELOR)
        assert counselor is not None
        if counselor.organization_id != organization_id:
            raise HTTPException(status_code=422, detail="辅导员与学生所属机构不一致")
    return organization, counselor_id


@router.get("", response_model=Page[StudentOut])
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    organization_id: int | None = None,
    grade: str | None = None,
    class_name: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = student_scope(_student_statement(), current_user)
    count_stmt = student_scope(select(func.count(Student.id)), current_user)

    conditions = []
    if keyword:
        conditions.append(or_(Student.student_no.contains(keyword), Student.name.contains(keyword)))
    if organization_id:
        conditions.append(Student.organization_id == organization_id)
    if grade:
        conditions.append(Student.grade == grade)
    if class_name:
        conditions.append(Student.class_name == class_name)
    if active_only:
        conditions.append(Student.is_active.is_(True))
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = db.scalar(count_stmt) or 0
    students = list(
        db.scalars(
            stmt.order_by(Student.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).unique()
    )
    case_map = _active_cases(db, [item.id for item in students])
    return Page(
        items=[student_out(item, case_map.get(item.id)) for item in students],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export.csv")
def export_students(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    students = list(
        db.scalars(
            student_scope(_student_statement(), current_user).order_by(
                Student.organization_id, Student.class_name, Student.student_no
            )
        ).unique()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "学号",
            "姓名",
            "性别",
            "机构编码",
            "机构名称",
            "专业",
            "年级",
            "班级",
            "手机号",
            "紧急联系人",
            "紧急联系电话",
            "辅导员账号",
            "辅导员姓名",
            "在校状态",
        ]
    )
    for item in students:
        writer.writerow(
            [
                item.student_no,
                item.name,
                item.gender or "",
                item.organization.code,
                item.organization.name,
                item.major or "",
                item.grade or "",
                item.class_name or "",
                item.phone or "",
                item.emergency_contact_name or "",
                item.emergency_contact_phone or "",
                item.counselor.username if item.counselor else "",
                item.counselor.full_name if item.counselor else "",
                "在校" if item.is_active else "停用",
            ]
        )
    add_audit_log(
        db,
        actor=current_user,
        action="EXPORT_STUDENTS",
        resource_type="STUDENT",
        resource_id=None,
        summary=f"导出学生数据，共 {len(students)} 条",
        request=request,
    )
    db.commit()
    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="students.csv"'},
    )


@router.post("/import", response_model=ImportResult)
def import_students(
    request: Request,
    file: UploadFile = File(...),
    update_existing: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.COUNSELOR}:
        raise HTTPException(status_code=403, detail="只有管理员和辅导员可以导入学生")
    raw = file.file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV 文件不能超过 5MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="CSV 文件必须使用 UTF-8 编码") from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV 文件没有表头")

    aliases = {
        "student_no": ["student_no", "学号"],
        "name": ["name", "姓名"],
        "gender": ["gender", "性别"],
        "organization_code": ["organization_code", "机构编码"],
        "major": ["major", "专业"],
        "grade": ["grade", "年级"],
        "class_name": ["class_name", "班级"],
        "phone": ["phone", "手机号"],
        "emergency_contact_name": ["emergency_contact_name", "紧急联系人"],
        "emergency_contact_phone": ["emergency_contact_phone", "紧急联系电话"],
        "counselor_username": ["counselor_username", "辅导员账号"],
    }

    def value(row: dict[str, str | None], key: str) -> str:
        for candidate in aliases[key]:
            if candidate in row and row[candidate] is not None:
                return str(row[candidate]).strip()
        return ""

    organizations = {
        item.code: item
        for item in db.scalars(select(Organization).where(Organization.is_active.is_(True)))
    }
    counselors = {
        item.username: item
        for item in db.scalars(
            select(User).where(User.role == UserRole.COUNSELOR, User.is_active.is_(True))
        )
    }
    existing_students = {item.student_no: item for item in db.scalars(select(Student))}

    created = 0
    updated = 0
    skipped = 0
    errors: list[ImportErrorItem] = []

    for row_number, row in enumerate(reader, start=2):
        try:
            student_no = value(row, "student_no")
            name = value(row, "name")
            organization_code = value(row, "organization_code")
            if not student_no or not name or not organization_code:
                raise ValueError("学号、姓名和机构编码不能为空")
            organization = organizations.get(organization_code)
            if organization is None:
                raise ValueError(f"机构编码不存在：{organization_code}")
            if (
                current_user.role == UserRole.COUNSELOR
                and organization.id != current_user.organization_id
            ):
                raise ValueError("辅导员只能导入本机构学生")

            counselor_username = value(row, "counselor_username")
            counselor = counselors.get(counselor_username) if counselor_username else None
            if current_user.role == UserRole.COUNSELOR:
                counselor = current_user
            elif counselor_username and counselor is None:
                raise ValueError(f"辅导员账号不存在：{counselor_username}")
            if counselor and counselor.organization_id != organization.id:
                raise ValueError("辅导员与学生所属机构不一致")

            student = existing_students.get(student_no)
            if student and not update_existing:
                skipped += 1
                continue
            values: dict[str, Any] = {
                "name": name,
                "gender": value(row, "gender") or None,
                "organization_id": organization.id,
                "major": value(row, "major") or None,
                "grade": value(row, "grade") or None,
                "class_name": value(row, "class_name") or None,
                "phone": value(row, "phone") or None,
                "emergency_contact_name": value(row, "emergency_contact_name") or None,
                "emergency_contact_phone": value(row, "emergency_contact_phone") or None,
                "counselor_id": counselor.id if counselor else None,
                "is_active": True,
            }
            if student:
                for field, field_value in values.items():
                    setattr(student, field, field_value)
                updated += 1
            else:
                student = Student(student_no=student_no, **values)
                db.add(student)
                existing_students[student_no] = student
                created += 1
        except ValueError as exc:
            skipped += 1
            errors.append(ImportErrorItem(row=row_number, message=str(exc)))

    add_audit_log(
        db,
        actor=current_user,
        action="IMPORT_STUDENTS",
        resource_type="STUDENT",
        resource_id=None,
        summary=f"导入学生：新增 {created}，更新 {updated}，跳过 {skipped}",
        request=request,
        extra_data={"errors": [item.model_dump() for item in errors[:50]]},
    )
    db.commit()
    return ImportResult(created=created, updated=updated, skipped=skipped, errors=errors[:100])


@router.post("", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.COUNSELOR}:
        raise HTTPException(status_code=403, detail="只有管理员和辅导员可以创建学生")
    _, counselor_id = _validate_student_assignment(
        db,
        current_user,
        payload.organization_id,
        payload.counselor_id,
    )
    student = Student(
        **payload.model_dump(exclude={"counselor_id"}),
        counselor_id=counselor_id,
    )
    db.add(student)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="学号已存在") from None
    add_audit_log(
        db,
        actor=current_user,
        action="CREATE_STUDENT",
        resource_type="STUDENT",
        resource_id=student.id,
        summary=f"创建学生：{student.name}（{student.student_no}）",
        request=request,
    )
    db.commit()
    student = db.scalar(_student_statement().where(Student.id == student.id))
    return student_out(student)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = db.scalar(_student_statement().where(Student.id == student_id))
    student = ensure_student_access(student, current_user)
    active_case = _active_cases(db, [student.id]).get(student.id)
    return student_out(student, active_case)


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.COUNSELOR}:
        raise HTTPException(status_code=403, detail="只有管理员和辅导员可以修改学生")
    student = db.scalar(_student_statement().where(Student.id == student_id))
    student = ensure_student_access(student, current_user)
    values = payload.model_dump(exclude_unset=True)
    organization_id = values.get("organization_id", student.organization_id)
    counselor_id = values.get("counselor_id", student.counselor_id)
    _, validated_counselor_id = _validate_student_assignment(
        db, current_user, organization_id, counselor_id
    )
    values["counselor_id"] = validated_counselor_id
    for field, field_value in values.items():
        setattr(student, field, field_value)
    add_audit_log(
        db,
        actor=current_user,
        action="UPDATE_STUDENT",
        resource_type="STUDENT",
        resource_id=student.id,
        summary=f"更新学生：{student.name}（{student.student_no}）",
        request=request,
    )
    db.commit()
    student = db.scalar(_student_statement().where(Student.id == student.id))
    active_case = _active_cases(db, [student.id]).get(student.id)
    return student_out(student, active_case)
