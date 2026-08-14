import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, hash_password, require_roles, revoke_all_sessions
from app.models.entities import Department, Role, Term, User
from app.schemas import DepartmentIn, TermIn, UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["administration"], dependencies=[Depends(csrf_protect)])
teacher = require_roles(Role.TEACHER)


@router.get("/directory/users", response_model=list[UserOut])
async def directory_users(
    grade: int | None = Query(default=None, ge=1, le=3),
    actor: User = Depends(require_roles(*list(Role))),
    db: AsyncSession = Depends(get_db),
):
    statement = select(User).where(User.term_id == actor.term_id, User.is_active.is_(True))
    if grade is not None:
        statement = statement.where(User.grade == grade)
    return list((await db.scalars(statement.order_by(User.name))).all())


@router.get("/users", response_model=list[UserOut])
async def users(
    actor: User = Depends(require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    statement = select(User).where(User.term_id == actor.term_id)
    if actor.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(User.department_id == actor.department_id)
    return list((await db.scalars(statement.order_by(User.name))).all())


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    data: UserCreate, _: User = Depends(teacher), db: AsyncSession = Depends(get_db)
):
    if await db.scalar(select(User.id).where(User.email == data.email.lower())):
        raise AppError(409, "email_exists", "이미 사용 중인 이메일입니다.")
    user = User(
        **data.model_dump(exclude={"email", "password"}),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    actor: User = Depends(teacher),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise AppError(404, "user_not_found", "사용자를 찾을 수 없습니다.")
    changed_security = False
    for key, value in data.model_dump(exclude_unset=True, exclude={"password"}).items():
        changed_security |= (
            key in {"role", "is_active", "department_id"} and getattr(user, key) != value
        )
        setattr(user, key, value)
    if data.password:
        user.password_hash = hash_password(data.password)
        changed_security = True
    if changed_security:
        await revoke_all_sessions(db, user)
    else:
        await db.commit()
    return user


@router.get("/departments")
async def departments(
    _: User = Depends(require_roles(*list(Role))), db: AsyncSession = Depends(get_db)
):
    return list((await db.scalars(select(Department).order_by(Department.name))).all())


@router.post("/departments", status_code=201)
async def create_department(
    data: DepartmentIn, _: User = Depends(teacher), db: AsyncSession = Depends(get_db)
):
    department = Department(**data.model_dump())
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return department


@router.get("/terms")
async def terms(_: User = Depends(require_roles(*list(Role))), db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(Term).order_by(Term.starts_on.desc()))).all())


@router.post("/terms", status_code=201)
async def create_term(data: TermIn, _: User = Depends(teacher), db: AsyncSession = Depends(get_db)):
    if data.ends_on < data.starts_on:
        raise AppError(422, "invalid_period", "종료일은 시작일 이후여야 합니다.")
    if data.is_current:
        await db.execute(update(Term).values(is_current=False))
    term = Term(**data.model_dump())
    db.add(term)
    await db.commit()
    await db.refresh(term)
    return term
