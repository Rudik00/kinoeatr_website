from fastapi import APIRouter, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from ..db import get_db
from ..utils.security import verify_password
from ..utils.jwt_token import create_access_token, decode_access_token
from ..database.madels_db import (
    Admins,
    HallSeat, CinemaHall,
    Movies,
    MovieSession,
    Reservation,
    ReservationSeat,
    Registered_users,
)

import datetime


bearer_scheme = HTTPBearer()

# в файле функционал для админов
# 1 - вход
#   1.1 - Админ панель
# 2 - Добавление
#   2.1 - Зал
#   2.2 - Фильм
#   2.3 - Сеанс
# 3 - Просмотр
#   3.1 - Зал
#   3.2 - Фильм
#   3.3 - Сеанс
#   3.4 - Бронирования
# 4 - Редактирование
#   4.1 - Зал
#   4.2 - Фильм
#   4.3 - Сеанс
# 5 - Удаление
#   5.1 - Зал (только если к нему нет сеансов)
#   5.2 - Фильм (только если к нему нет сеансов)
#   5.3 - Сеанс


# admin.py — создаем роутер
router = APIRouter(prefix="/admin", tags=["Admin"])


# функция для получения текущего админа из токена
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload is None or payload.get("role") != "admin":
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_INVALID_TOKEN",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )
        return payload
    except Exception as e:
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# Защищённый роут — только админов
@router.get("/api/me")
async def admin_me(current_admin: dict = Depends(get_current_admin)):
    return {"message": f"Добро пожаловать, {current_admin['sub']}"}


##############################################################################################
#                                      1 - ВХОД
# ____________________________________________________________________________________________
#                                      АДМИН ПАНЕЛЬ
# ____________________________________________________________________________________________
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
    try:
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

    except Exception as e:
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


##############################################################################################
#                                      2 - ДОБАВЛЕНИЕ
# ____________________________________________________________________________________________
#                                      2.1 - ЗАЛ
# ____________________________________________________________________________________________

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
            raise ValueError("ADMIN_HALL_ROW_NUMBER_INVALID")
        return v

    @field_validator("seats_count")
    @classmethod
    def validate_seats_count(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("ADMIN_HALL_SEATS_COUNT_INVALID")
        return v


# 2. Валидация всего запроса на создание зала
class HallCreate(BaseModel):
    name: str
    rows: List[RowConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip() or len(v) > 100:
            raise ValueError("ADMIN_HALL_NAME_INVALID")
        return v.strip()

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v):
        if not v:
            raise ValueError("ADMIN_HALL_ROWS_EMPTY")
        # Проверка на дубликаты номеров рядов
        row_numbers = [r.row_number for r in v]
        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError("ADMIN_HALL_DUPLICATE_ROW_NUMBERS")
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
                        "msg": "ADMIN_HALL_NAME_EXISTS",
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


# __________________________________________________________________________________________________
#                                      2.2 - ФИЛЬМ
# __________________________________________________________________________________________________
# Валидация данных фильма
class MovieCreate(BaseModel):
    name: str
    duration: int
    description: str
    release_date: str
    preview_foto: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip() or len(v) > 100:
            raise ValueError("ADMIN_MOVIE_NAME_INVALID")
        return v.strip()

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError("ADMIN_MOVIE_DURATION_INVALID")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if not v.strip() or v.strip() == "":
            raise ValueError("ADMIN_MOVIE_DESCRIPTION_EMPTY")
        return v.strip()

    @field_validator("release_date")
    @classmethod
    def validate_release_date(cls, v):
        # Проверка даты с пособием datetime или regex
        # Для простоты примем формат "YYYY-MM-DD"
        try:
            datetime.datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("ADMIN_MOVIE_RELEASE_DATE_INVALID")
        return v.strip()

    @field_validator("preview_foto")
    @classmethod
    def validate_preview_foto(cls, v):
        if not v.strip() or v.strip() == "":
            raise ValueError("ADMIN_MOVIE_PREVIEW_FOTO_EMPTY")
        return v.strip()


# Эндпоинт для создания фильма
@router.post("/api/movies")
async def create_movie(
    movie_data: MovieCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Создаем объект фильма
        new_movie = Movies(
            name=movie_data.name,
            duration=movie_data.duration,
            description=movie_data.description,
            release_date=movie_data.release_date,
            preview_foto=movie_data.preview_foto
        )
        existing_movies = (
            await db.execute(select(Movies))
        ).scalars().all()
        if movie_data.name in [movie.name for movie in existing_movies]:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_MOVIE_NAME_EXISTS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        db.add(new_movie)

        # flush() в асинхронном режиме требует await
        await db.flush()
        await db.commit()
        return {"status": "success", "movie_id": new_movie.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# ____________________________________________________________________________________________
#                                      2.3 - СЕАНС
# ____________________________________________________________________________________________

class MovieSessionCreate(BaseModel):
    movie_id: int
    hall_id: int
    starts_at: str
    base_price: int

    @field_validator("movie_id")
    @classmethod
    def validate_movie_id(cls, v):
        if v <= 0:
            raise ValueError("ADMIN_SESSION_MOVIE_ID_INVALID")
        return v

    @field_validator("hall_id")
    @classmethod
    def validate_hall_id(cls, v):
        if v <= 0:
            raise ValueError("ADMIN_SESSION_HALL_ID_INVALID")
        return v

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, v):
        value = v.strip()
        if not value:
            raise ValueError("ADMIN_SESSION_STARTS_AT_EMPTY")
        try:
            datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("ADMIN_SESSION_STARTS_AT_INVALID")
        return value

    @field_validator("base_price")
    @classmethod
    def validate_base_price(cls, v):
        if v <= 0:
            raise ValueError("ADMIN_SESSION_BASE_PRICE_INVALID")
        return v


@router.post("/api/sessions")
async def create_movie_session(
    session_data: MovieSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        starts_at_dt = datetime.datetime.fromisoformat(session_data.starts_at)
        if starts_at_dt <= datetime.datetime.now():
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_START_TIME_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        movie = await db.get(Movies, session_data.movie_id)
        if movie is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_MOVIE_ID_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        hall = await db.get(CinemaHall, session_data.hall_id)
        if hall is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_HALL_ID_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        conflict = (
            await db.execute(
                select(MovieSession).filter_by(
                    hall_id=session_data.hall_id,
                    starts_at=starts_at_dt,
                )
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_CONFLICT",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        new_session = MovieSession(
            movie_id=session_data.movie_id,
            hall_id=session_data.hall_id,
            starts_at=starts_at_dt,
            base_price=session_data.base_price,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return {"status": "success", "session_id": new_session.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


##############################################################################################
#                                      3 - ПРОСМОТР
# ____________________________________________________________________________________________
#                                      3.1 - ЗАЛ
# ____________________________________________________________________________________________

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


@router.get("/api/halls/{hall_id}")
async def get_cinema_hall(
    hall_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    hall = await db.get(CinemaHall, hall_id)
    if hall is None:
        raise HTTPException(status_code=404, detail="Зал не найден")

    seats = (
        await db.execute(select(HallSeat).filter_by(hall_id=hall_id))
    ).scalars().all()

    # Группируем по рядам: берём первый seat каждого ряда для category
    rows_map: dict = {}
    for seat in seats:
        r = seat.seat_row
        if r not in rows_map:
            rows_map[r] = {"row_number": r, "seats_count": 0, "category": seat.category}
        rows_map[r]["seats_count"] += 1

    return {
        "id": hall.id,
        "name": hall.name_hall,
        "rows": sorted(rows_map.values(), key=lambda x: x["row_number"]),
    }


# ____________________________________________________________________________________________
#                                      3.2 - ФИЛЬМ
# ____________________________________________________________________________________________

@router.get("/api/movies")
async def list_movies(db: AsyncSession = Depends(get_db)):
    result_movies = await db.execute(select(Movies))
    movies = result_movies.scalars().all()

    return {
        "movies": [
            {
                "id": movie.id,
                "name": movie.name,
                "duration": movie.duration,
                "release_date": movie.release_date,
                "description": movie.description,
                "preview_foto": movie.preview_foto,
            }
            for movie in movies
        ]
    }


# ____________________________________________________________________________________________
#                                      3.3 - СЕАНС
# ____________________________________________________________________________________________

@router.get("/api/sessions")
async def list_movie_sessions(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    sessions = (
        await db.execute(
            select(MovieSession).order_by(MovieSession.starts_at.asc())
        )
    ).scalars().all()

    movies = (await db.execute(select(Movies))).scalars().all()
    halls = (await db.execute(select(CinemaHall))).scalars().all()

    movie_name_by_id = {movie.id: movie.name for movie in movies}
    hall_name_by_id = {hall.id: hall.name_hall for hall in halls}

    return {
        "sessions": [
            {
                "id": session.id,
                "movie_id": session.movie_id,
                "movie_name": movie_name_by_id.get(session.movie_id),
                "hall_id": session.hall_id,
                "hall_name": hall_name_by_id.get(session.hall_id),
                "starts_at": session.starts_at.isoformat(),
                "base_price": session.base_price,
            }
            for session in sessions
        ]
    }


# ____________________________________________________________________________________________
#                                      3.4 - БРОНИРОВАНИЯ
# ____________________________________________________________________________________________
@router.get("/api/bookings")
async def list_bookings(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    sessions = (
        await db.execute(
            select(MovieSession).order_by(MovieSession.starts_at.asc())
        )
    ).scalars().all()

    movies = (await db.execute(select(Movies))).scalars().all()
    halls = (await db.execute(select(CinemaHall))).scalars().all()

    movie_name_by_id = {movie.id: movie.name for movie in movies}
    hall_name_by_id = {hall.id: hall.name_hall for hall in halls}

    return {
        "sessions": [
            {
                "id": session.id,
                "movie_id": session.movie_id,
                "movie_name": movie_name_by_id.get(session.movie_id),
                "hall_id": session.hall_id,
                "hall_name": hall_name_by_id.get(session.hall_id),
                "starts_at": session.starts_at.isoformat(),
                "base_price": session.base_price,
            }
            for session in sessions
        ]
    }


@router.get("/api/bookings/{session_id}")
async def list_bookings_for_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    session = await db.get(MovieSession, session_id)
    if session is None:
        raise RequestValidationError(
            errors=[
                {
                    "msg": "SESSION_NOT_FOUND",
                    "loc": (),
                    "type": "value_error",
                }
            ]
        )

    movie = await db.get(Movies, session.movie_id)
    movie_name = movie.name if movie is not None else None

    hall_seats = (
        await db.execute(select(HallSeat).filter_by(hall_id=session.hall_id))
    ).scalars().all()
    seat_by_id = {seat.id: seat for seat in hall_seats}
    total_seats = len(hall_seats)

    reservation_seats = (
        await db.execute(
            select(ReservationSeat).filter_by(session_id=session_id)
        )
    ).scalars().all()

    reservation_ids = {item.reservation_id for item in reservation_seats}
    reservations = (
        await db.execute(
            select(Reservation).where(Reservation.id.in_(reservation_ids))
        )
    ).scalars().all() if reservation_ids else []
    reservation_by_id = {reservation.id: reservation for reservation in reservations}

    user_ids = {
        reservation.user_id
        for reservation in reservations
        if reservation.user_id is not None
    }
    users = (
        await db.execute(
            select(Registered_users).where(Registered_users.id.in_(user_ids))
        )
    ).scalars().all() if user_ids else []
    user_email_by_id = {user.id: user.email_user for user in users}

    bookings_items = []
    for item in reservation_seats:
        reservation = reservation_by_id.get(item.reservation_id)
        seat = seat_by_id.get(item.seat_id)

        guest_email = None
        if reservation is not None:
            if reservation.user_id is not None:
                guest_email = user_email_by_id.get(reservation.user_id)
            if not guest_email:
                guest_email = reservation.guest_email

        seat_label = "-"
        if seat is not None:
            seat_label = f"Ряд {seat.seat_row}, место {seat.seat_number}"

        bookings_items.append(
            {
                "id": item.id,
                "reservation_id": item.reservation_id,
                "email": guest_email,
                "seat": seat_label,
            }
        )

    return {
        "session": {
            "id": session.id,
            "movie_id": session.movie_id,
            "movie_name": movie_name,
            "hall_id": session.hall_id,
            "starts_at": session.starts_at.isoformat(),
        },
        "bookings_count": len(bookings_items),
        "free_seats_count": max(total_seats - len(bookings_items), 0),
        "bookings": bookings_items,
    }


##############################################################################################
#                                      4 - РЕДАКТИРОВАНИЕ
# ____________________________________________________________________________________________
#                                      4.1 - ЗАЛ
# ____________________________________________________________________________________________
# Валидация запроса на редактирование зала (использует RowConfig из секции 2.1)
class HallEdit(BaseModel):
    name: str
    rows: List[RowConfig]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip() or len(v) > 100:
            raise ValueError("ADMIN_HALL_NAME_INVALID")
        return v.strip()

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v):
        if not v:
            raise ValueError("ADMIN_HALL_ROWS_EMPTY")
        # Проверка на дубликаты номеров рядов
        row_numbers = [r.row_number for r in v]
        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError("DUPLICATE_ROW_NUMBERS")
        return v


@router.put("/api/halls_edit/{hall_id}")
async def edit_cinema_hall(
    hall_id: int,
    hall_data: HallEdit,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        hall = await db.get(CinemaHall, hall_id)
        if hall is None:
            raise HTTPException(status_code=404, detail="Зал не найден")

        existing_halls = (
            await db.execute(select(CinemaHall))
        ).scalars().all()
        if hall_data.name in [
            h.name_hall for h in existing_halls if h.id != hall_id
        ]:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_HALL_NAME_EXISTS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        hall.name_hall = hall_data.name

        # Удаляем старые места и создаем новые
        old_seats = (
            await db.execute(select(HallSeat).filter_by(hall_id=hall_id))
        ).scalars().all()
        for seat in old_seats:
            await db.delete(seat)
        await db.flush()

        for row in hall_data.rows:
            for seat_num in range(1, row.seats_count + 1):
                seat = HallSeat(
                    hall_id=hall_id,
                    seat_row=row.row_number,
                    seat_number=seat_num,
                    category=row.category
                )
                db.add(seat)

        await db.commit()
        await db.refresh(hall)
        return {"status": "success", "hall_id": hall.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, (RequestValidationError, HTTPException)):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# ____________________________________________________________________________________________
#                                      4.2 - ФИЛЬМ
# ____________________________________________________________________________________________
# Использует MovieCreate из секции 2.2 (идентичные поля и валидация)
@router.put("/api/movies_edit/{movie_id}")
async def edit_movie(
    movie_id: int,
    movie_data: MovieCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        movie = await db.get(Movies, movie_id)
        if movie is None:
            raise HTTPException(status_code=404, detail="Фильм не найден")

        existing_movies = (
            await db.execute(select(Movies))
        ).scalars().all()
        if movie_data.name in [
            m.name for m in existing_movies if m.id != movie_id
        ]:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_MOVIE_NAME_EXISTS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        movie.name = movie_data.name
        movie.duration = movie_data.duration
        movie.description = movie_data.description
        movie.release_date = movie_data.release_date
        movie.preview_foto = movie_data.preview_foto

        await db.commit()
        await db.refresh(movie)
        return {"status": "success", "movie_id": movie.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, (RequestValidationError, HTTPException)):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# ____________________________________________________________________________________________
#                                      4.3 - СЕАНС
# ____________________________________________________________________________________________
# Использует MovieSessionCreate из секции 2.3 (идентичные поля и валидация)
@router.put("/api/sessions_edit/{session_id}")
async def edit_movie_session(
    session_id: int,
    session_data: MovieSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        session = await db.get(MovieSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Сеанс не найден")

        starts_at_dt = datetime.datetime.fromisoformat(session_data.starts_at)
        if starts_at_dt <= datetime.datetime.now():
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_START_TIME_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        movie = await db.get(Movies, session_data.movie_id)
        if movie is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_MOVIE_ID_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        hall = await db.get(CinemaHall, session_data.hall_id)
        if hall is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_HALL_ID_INVALID",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        conflict = (
            await db.execute(
                select(MovieSession).where(
                    MovieSession.hall_id == session_data.hall_id,
                    MovieSession.starts_at == starts_at_dt,
                    MovieSession.id != session_id,
                )
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_CONFLICT",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        session.movie_id = session_data.movie_id
        session.hall_id = session_data.hall_id
        session.starts_at = starts_at_dt
        session.base_price = session_data.base_price

        await db.commit()
        await db.refresh(session)
        return {"status": "success", "session_id": session.id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, (RequestValidationError, HTTPException)):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


##############################################################################################
#                                      5 - УДАЛЕНИЕ
# ____________________________________________________________________________________________
#                                      5.1 - ЗАЛ (только если к нему нет сеансов)
# ____________________________________________________________________________________________

@router.delete("/api/halls/{hall_id}")
async def delete_cinema_hall(
    hall_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        hall = await db.get(CinemaHall, hall_id)
        if hall is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_HALL_NOT_FOUND",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        existing_session = (
            await db.execute(select(MovieSession).filter_by(hall_id=hall_id))
        ).scalar_one_or_none()
        if existing_session is not None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_HALL_DELETE_HAS_SESSIONS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        await db.delete(hall)
        await db.commit()
        return {"status": "success", "deleted_hall_id": hall_id}

    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# ____________________________________________________________________________________________
#                                      5.2 - ФИЛЬМ (только если к нему нет сеансов)
# ____________________________________________________________________________________________

@router.delete("/api/movies/{movie_id}")
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        movie = await db.get(Movies, movie_id)
        if movie is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_MOVIE_NOT_FOUND",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        result_session = await db.execute(
            select(MovieSession).filter_by(movie_id=movie_id)
        )
        existing_session = result_session.scalar_one_or_none()
        if existing_session is not None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_MOVIE_DELETE_HAS_SESSIONS",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        await db.delete(movie)
        await db.commit()
        return {"status": "success", "deleted_movie_id": movie_id}
    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# ____________________________________________________________________________________________
#                                      5.3 - СЕАНС
# ____________________________________________________________________________________________

@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    try:
        session = await db.get(MovieSession, session_id)
        if session is None:
            raise RequestValidationError(
                errors=[
                    {
                        "msg": "ADMIN_SESSION_NOT_FOUND",
                        "loc": (),
                        "type": "value_error",
                    }
                ]
            )

        await db.delete(session)
        await db.commit()
        return {"status": "success", "deleted_session_id": session_id}
    except Exception as e:
        await db.rollback()
        if isinstance(e, RequestValidationError):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


##############################################################################################
#                                      6 - СТАТИСТИКА
# ____________________________________________________________________________________________

@router.get("/api/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    movies_count = (await db.execute(select(func.count()).select_from(Movies))).scalar()
    sessions_count = (await db.execute(select(func.count()).select_from(MovieSession))).scalar()
    halls_count = (await db.execute(select(func.count()).select_from(CinemaHall))).scalar()
    bookings_count = (await db.execute(select(func.count()).select_from(ReservationSeat))).scalar()
    return {
        "movies_count": movies_count,
        "sessions_count": sessions_count,
        "halls_count": halls_count,
        "bookings_count": bookings_count,
    }
