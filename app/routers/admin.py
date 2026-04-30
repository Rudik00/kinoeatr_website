from fastapi import APIRouter, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..utils.security import hash_password, verify_password
from ..utils.jwt_token import create_access_token, decode_access_token
from ..database.madels_db import Admins

bearer_scheme = HTTPBearer()


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Не авторизован")
    return payload

# в файле функционал для админов
# 1 - вход в админ панель
# 2 - добавление зала
# 3 - добавление фильма
# 4 - добавление сеанса
# 5 - просмотр всех бронирований
# 6 - просмотр всех фильмов, залов, сеансов
# 7 - редактирование фильма, зала, сеанса
# 8 - удаление фильма, зала, сеанса


# admin.py — создаем роутер
router = APIRouter(prefix="/admin", tags=["Admin"])


# 1 - вход в админ панель
class AdminLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        if not v:
            raise ValueError("ADMIN_LOGIN_EMAIL_EMPTY")
        if "@" not in v:
            raise ValueError("ADMIN_LOGIN_EMAIL_INVALID")
        return v.lower()

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v):
        if not v or len(v) < 1:
            raise ValueError("ADMIN_LOGIN_PASSWORD_EMPTY")
        if len(v) < 8:
            raise ValueError("ADMIN_LOGIN_PASSWORD_INVALID")
        return v


# 1 - вход в админ панель
@router.post("/login")
async def admin_login(
    admin: AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    # Проверяешь, существует ли админ с таким email
    result = await db.execute(
        select(Admins).filter_by(email_admin=admin.email)
    )
    existing_admin = result.scalar_one_or_none()

    # Если админа нет, возвращаешь ошибку
    if not existing_admin:
        raise RequestValidationError(
            errors=[{"msg": "ADMIN_LOGIN_NO_EMAIL", "loc": (), "type": "value_error"}]
        )

    # Проверяешь пароль
    if not verify_password(admin.password, existing_admin.password_admin):
        raise RequestValidationError(
            errors=[{"msg": "ADMIN_LOGIN_PASSWORD_INVALID", "loc": (), "type": "value_error"}]
        )

    token = create_access_token({"sub": existing_admin.email_admin, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


# Защищённый роут — только для авторизованных админов
@router.get("/me")
async def admin_me(current_admin: dict = Depends(get_current_admin)):
    return {"message": f"Добро пожаловать, {current_admin['sub']}"}
