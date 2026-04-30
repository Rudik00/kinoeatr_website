from fastapi import APIRouter, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..db import get_db
from ..utils.security import verify_password
from ..utils.jwt_token import create_access_token, decode_access_token
from ..database.madels_db import (
    Admins,
    HallSeat, CinemaHall,
)

bearer_scheme = HTTPBearer()

# в файле функционал для админов
# 1 - вход в админ панель
# 2 - добавление зала
# 3 - просмотр залов
#  - добавление фильма
#  - добавление сеанса
#  - просмотр всех бронирований
#  - просмотр всех фильмов, сеансов
#  - редактирование фильма, зала, сеанса
#  - удаление фильма, зала, сеанса


# admin.py — создаем роутер
router = APIRouter(prefix="/admin", tags=["Admin"])


# функция для получения текущего админа из токена
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Не авторизован")
    return payload


# Защищённый роут — только админов
@router.get("/api/me")
async def admin_me(current_admin: dict = Depends(get_current_admin)):
    return {"message": f"Добро пожаловать, {current_admin['sub']}"}


# ________________________________________________________________________________
#                                      1 - ВХОД В АДМИН ПАНЕЛЬ
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


@router.post("/api/login")
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
            errors=[
                {
                    "msg": "ADMIN_LOGIN_NO_EMAIL",
                    "loc": (),
                    "type": "value_error",
                }
            ]
        )

    # Проверяешь пароль
    if not verify_password(admin.password, existing_admin.password_admin):
        raise RequestValidationError(
            errors=[
                {
                    "msg": "ADMIN_LOGIN_PASSWORD_INVALID",
                    "loc": (),
                    "type": "value_error",
                }
            ]
        )

    token = create_access_token(
        {"sub": existing_admin.email_admin, "role": "admin"}
    )
    return {"access_token": token, "token_type": "bearer"}


# ________________________________________________________________________________
#                                   2 - ДОБАВЛЕНИЕ ЗАЛА
# 1. Валидация конкретного ряда
class RowConfig(BaseModel):
    row_number: int
    seats_count: int
    category: str = "standard"

    @field_validator("row_number")
    @classmethod
    def validate_row_number(cls, v):
        # Поднял лимит, 20 может быть мало для больших залов
        if v <= 0 or v > 50:
            raise ValueError("ROW_NUMBER_INVALID")
        return v

    @field_validator("seats_count")
    @classmethod
    def validate_seats_count(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("SEATS_COUNT_INVALID")
        return v


# 2. Валидация всего запроса на создание зала
class HallCreate(BaseModel):
    name: str
    rows: List[RowConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip() or len(v) > 100:
            raise ValueError("HALL_NAME_INVALID")
        return v.strip()

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v):
        if not v:
            raise ValueError("HALL_ROWS_EMPTY")
        # Проверка на дубликаты номеров рядов
        row_numbers = [r.row_number for r in v]
        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError("DUPLICATE_ROW_NUMBERS")
        return v


# 3. Эндпоинт (с учетом асинхронности)
@router.post("/api/halls")
async def create_cinema_hall(
    hall_data: HallCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Создаем объект зала
        new_hall = CinemaHall(name_hall=hall_data.name)
        existing_halls = (
            await db.execute(select(CinemaHall))
        ).scalars().all()
        if hall_data.name in [hall.name_hall for hall in existing_halls]:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "HALL_NAME_EXISTS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        db.add(new_hall)

        # flush() в асинхронном режиме требует await
        await db.flush()

        # Генерируем места
        for row in hall_data.rows:
            for seat_num in range(1, row.seats_count + 1):
                seat = HallSeat(
                    hall_id=new_hall.id,
                    seat_row=row.row_number,
                    seat_number=seat_num,
                    category=row.category
                )
                db.add(seat)

        await db.commit()
        return {"status": "success", "hall_id": new_hall.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# _________________________________________________________________________________________________
#                                   3 - ПРОСМОТР ЗАЛОВ

@router.get("/api/halls")
async def list_cinema_halls(db: AsyncSession = Depends(get_db)):
    result_cinema_halls = await db.execute(select(CinemaHall))
    result_hall_seats = await db.execute(select(HallSeat))

    halls = result_cinema_halls.scalars().all()
    hall_seats = result_hall_seats.scalars().all()

    return {
        "halls": [
            {
                "id": hall.id,
                "name": hall.name_hall,
                "rows_count": len({
                    seat.seat_row
                    for seat in hall_seats
                    if seat.hall_id == hall.id
                }),
                "total_seats": len([
                    seat
                    for seat in hall_seats
                    if seat.hall_id == hall.id
                ]),
            }
            for hall in halls
        ]
    }


# _________________________________________________________________________________________________
#                                    - УДАЛЕНИЕ

# Удаление зала (только если к нему нет сеансов)
@router.delete("/api/halls/{hall_id}")
async def delete_cinema_hall(
    hall_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    hall = await db.get(CinemaHall, hall_id)
    if hall is None:
        raise HTTPException(status_code=404, detail="Зал не найден")

    try:
        await db.delete(hall)
        await db.commit()
        return {"status": "success", "deleted_hall_id": hall_id}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=(
                "Не удалось удалить зал. Возможно, к нему привязаны сеансы."
            ),
        )
