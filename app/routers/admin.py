from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..utils.security import hash_password, verify_password
from ..database.madels_db import Admins

# в файле функционал для админов
# 1 - регистрация админа
# 2 - вход в админ панель
# 3 - добавление зала
# 4 - добавление фильма
# 5 - добавление сеанса
# 6 - просмотр всех бронирований
# 7 - просмотр всех фильмов, залов, сеансов
# 8 - редактирование фильма, зала, сеанса
# 9 - удаление фильма, зала, сеанса


# admin.py — создаем роутер
router = APIRouter(prefix="/admin", tags=["Admin"])


# 1 - регистрация админа
class AdminRegister(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def email_must_be_lowercase(cls, v):
        if not v or v.strip() == "":
            raise ValueError("ADMIN_REGISTER_EMAIL_EMPTY")
        if "@" not in v:
            raise ValueError("ADMIN_REGISTER_EMAIL_INVALID")
        return v.lower()

    @field_validator("password", mode="before")
    @classmethod
    def password_must_be_valid(cls, v):
        if not v or v.strip() == "":
            raise ValueError("ADMIN_REGISTER_PASSWORD_EMPTY")
        if len(v) < 8:
            raise ValueError("ADMIN_REGISTER_PASSWORD_INVALID")
        return v


# 2 - вход в админ панель
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


# 1 - регистрация админа
@router.post("/register")
async def admin_register(
    admin: AdminRegister,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Создаешь объект модели
        new_admin = Admins(
            email_admin=admin.email,
            password_admin=hash_password(admin.password),  # функция хеша
        )

        # Добавляешь в БД
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)

        return {"id": new_admin.id, "message": "Admin created"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()  # откатываешь изменения при ошибке
        raise HTTPException(status_code=500, detail=str(e))


# 2 - вход в админ панель
@router.post("/login")
async def admin_login(
    admin: AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Проверяешь, существует ли админ с таким email
        result = await db.execute(
            select(Admins).filter_by(email_admin=admin.email)
        )
        existing_admin = result.scalar_one_or_none()

        if not existing_admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        # Проверяешь пароль
        if not verify_password(admin.password, existing_admin.password_admin):
            raise HTTPException(status_code=401, detail="Invalid password")

        return {"message": f"Admin {admin.email} logged in successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
