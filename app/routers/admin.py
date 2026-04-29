from fastapi import APIRouter, FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator


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
def admin_register(admin: AdminRegister):
    #логика добавления админа в базу данных
    email = admin.email
    password = admin.password

    
    return {"message": f"Admin {admin.email} registered successfully"}


# 2 - вход в админ панель
@router.post("/login")
def admin_login(admin: AdminLogin):
    return {"message": f"Admin {admin.email} logged in successfully"}
