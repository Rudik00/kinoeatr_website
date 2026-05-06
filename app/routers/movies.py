import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, StringConstraints
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..database.madels_db import (
    CinemaHall,
    EmailVerificationToken,
    HallSeat,
    MovieSession,
    Movies,
    Registered_users,
    Reservation,
    ReservationSeat,
)
from ..utils.email import build_verification_url, send_verification_email
from ..utils.jwt_token import create_access_token_user, decode_access_token_user
from ..utils.security import hash_password, verify_password

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)

# Реализованы следующие страницы:
# 1 - Проверка токена
# 2 - Регистрация и авторизация
# 3 - Главная страница с каталогом фильмов
# 4 - Страница фильма с его сеансами
# 5 - Страница зала с выбором мест
# 6 - Подтверждение бронирования
# 7 - Личный кабинет с историей бронирований и настройками профиля


##############################################################################################
#                                      1 - ПРОВЕРКА ТОКЕНА
# ___________________________________________________________________________________________
def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """Возвращает payload если токен валидный, иначе None."""
    if credentials is None:
        return None
    payload = decode_access_token_user(credentials.credentials)
    if payload is None or payload.get("role") != "user":
        return None
    return payload


def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """Возвращает payload пользователя или 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    payload = decode_access_token_user(credentials.credentials)
    if payload is None or payload.get("role") != "user":
        raise HTTPException(status_code=401, detail="Неверный или просроченный токен")
    return payload


def category_price(category: str, base_price: int) -> int:
    if category == "vip":
        return round(base_price * 1.5)
    if category == "premium":
        return round(base_price * 2)
    return base_price


##############################################################################################
#                                      2 - РЕГИСТРАЦИЯ И АВТОРИЗАЦИЯ
# ____________________________________________________________________________________________
class UserLoginData(BaseModel):
    email: str
    password: str


class UserRegisterData(BaseModel):
    name: str
    surname: str
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=6)]


class BookingCreateData(BaseModel):
    session_id: int
    seat_ids: list[int]


class UserSettingsUpdateData(BaseModel):
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: Annotated[
        str | None,
        StringConstraints(min_length=6),
    ] = None


@router.post("/api/user/register")
async def user_register(data: UserRegisterData, db: AsyncSession = Depends(get_db)):
    email_norm = str(data.email).strip().lower()

    existing = (
        await db.execute(
            select(Registered_users).where(Registered_users.email_user == email_norm)
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.is_verified:
            raise HTTPException(
                status_code=409,
                detail="Пользователь с таким email уже существует",
            )

        # Пользователь есть, но не подтверждён: перевыпускаем токен.
        existing.name_user = data.name
        existing.surname_user = data.surname
        existing.password_user = hash_password(data.password)

        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        old_token = (
            await db.execute(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == existing.id
                )
            )
        ).scalar_one_or_none()

        if old_token is not None:
            old_token.token = verification_token
            old_token.expires_at = expires_at
        else:
            db.add(EmailVerificationToken(
                user_id=existing.id,
                token=verification_token,
                expires_at=expires_at,
            ))

        await db.commit()

        sent, reason = await send_verification_email(
            existing.email_user,
            verification_token,
        )
        if sent:
            return {
                "message": (
                    "Аккаунт уже создан, но не подтверждён. "
                    "Мы отправили новое письмо подтверждения."
                )
            }

        return {
            "message": (
                "Аккаунт уже создан, но не подтверждён. "
                "Почтовый сервис не настроен, используйте ссылку вручную."
            ),
            "dev_verify_url": build_verification_url(verification_token),
            "email_error": reason,
        }

    user = Registered_users(
        name_user=data.name,
        surname_user=data.surname,
        email_user=email_norm,
        password_user=hash_password(data.password),
        is_verified=False,
    )
    db.add(user)
    await db.flush()   # получаем user.id без коммита

    verification_token = secrets.token_urlsafe(32)
    # В БД колонка TIMESTAMP WITHOUT TIME ZONE, сохраняем naive datetime.
    expires_at = datetime.utcnow() + timedelta(hours=24)
    db.add(EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=expires_at,
    ))
    await db.commit()

    sent, reason = await send_verification_email(user.email_user, verification_token)
    if sent:
        return {"message": "Письмо с подтверждением отправлено на вашу почту"}

    # Dev fallback: показываем ссылку подтверждения, если SMTP ещё не настроен.
    return {
        "message": (
            "Почтовый сервис не настроен. Откройте ссылку подтверждения вручную."
        ),
        "dev_verify_url": build_verification_url(verification_token),
        "email_error": reason,
    }


@router.post("/api/user/login")
async def user_login(data: UserLoginData, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(Registered_users).where(Registered_users.email_user == data.email)
        )
    ).scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_user):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Пожалуйста, подтвердите ваш email перед входом",
        )

    token = create_access_token_user(
        {"sub": user.email_user, "role": "user", "user_id": user.id}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/api/user/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()

    record = (
        await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token == token
            )
        )
    ).scalar_one_or_none()

    if record is None:
        return HTMLResponse(
            content="<h2>Ссылка недействительна или уже использована.</h2>",
            status_code=400,
        )

    if now > record.expires_at:
        await db.delete(record)
        await db.commit()
        return HTMLResponse(
            content="<h2>Ссылка истекла. Зарегистрируйтесь повторно.</h2>",
            status_code=400,
        )

    user = (
        await db.execute(
            select(Registered_users).where(
                Registered_users.id == record.user_id
            )
        )
    ).scalar_one_or_none()

    if user is None:
        await db.delete(record)
        await db.commit()
        return HTMLResponse(
            content="<h2>Пользователь не найден.</h2>",
            status_code=400,
        )

    user.is_verified = True
    await db.delete(record)
    await db.commit()

    jwt = create_access_token_user(
        {"sub": user.email_user, "role": "user", "user_id": user.id}
    )
    # Редиректим на /movies с токеном в hash — JS подхватит и сохранит
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Email подтверждён</title></head>
        <body>
          <p>Email подтверждён, перенаправляем…</p>
          <script>
            localStorage.setItem('user_token', '{jwt}');
            window.location.href = '/movies';
          </script>
        </body>
        </html>
        """,
        status_code=200,
    )


@router.get("/api/check-auth")
async def check_auth(
    current_user=Depends(get_current_user_optional),
):
    if current_user is None:
        return {"authenticated": False}
    return {"authenticated": True, "email": current_user.get("sub")}


##############################################################################################
#                                      3 - ГЛАВНАЯ СТРАНИЦА
# ____________________________________________________________________________________________
@router.get("/api/movies")
async def list_movies_page(db: AsyncSession = Depends(get_db)):
    movies = (await db.execute(select(Movies))).scalars().all()
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


##############################################################################################
#                                      4 - СТРАНИЦА ФИЛЬМА
# ____________________________________________________________________________________________
@router.get("/api/movies/{movie_id}")
async def movie_detail_page(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(Movies, movie_id)
    if not movie:
        return {"error": "Фильм не найден"}

    sessions = (
        await db.execute(
            select(MovieSession)
            .where(MovieSession.movie_id == movie_id)
            .order_by(MovieSession.starts_at.asc())
        )
    ).scalars().all()

    halls = (await db.execute(select(CinemaHall))).scalars().all()
    hall_name_by_id = {h.id: h.name_hall for h in halls}

    return {
        "id": movie.id,
        "name": movie.name,
        "duration": movie.duration,
        "release_date": movie.release_date,
        "description": movie.description,
        "preview_foto": movie.preview_foto,
        "sessions": [
            {
                "id": session.id,
                "hall_id": session.hall_id,
                "hall_name": hall_name_by_id.get(session.hall_id),
                "starts_at": session.starts_at.isoformat(),
                "base_price": session.base_price,
            }
            for session in sessions
        ],
    }


##############################################################################################
#                                      5 - СТРАНИЦА ЗАЛА
# ____________________________________________________________________________________________
@router.get("/api/sessions/{session_id}")
async def session_detail(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(MovieSession, session_id)
    if not session:
        return {"error": "Сеанс не найден"}

    movie = await db.get(Movies, session.movie_id)
    hall = await db.get(CinemaHall, session.hall_id)

    # Все места зала
    seats = (
        await db.execute(
            select(HallSeat)
            .where(HallSeat.hall_id == session.hall_id)
            .order_by(HallSeat.seat_row, HallSeat.seat_number)
        )
    ).scalars().all()

    # Занятые места на этот сеанс
    booked_seat_ids = set(
        (
            await db.execute(
                select(ReservationSeat.seat_id)
                .where(ReservationSeat.session_id == session_id)
            )
        ).scalars().all()
    )

    return {
        "session": {
            "id": session.id,
            "starts_at": session.starts_at.isoformat(),
            "base_price": session.base_price,
            "movie_name": movie.name if movie else None,
            "hall_name": hall.name_hall if hall else None,
        },
        "seats": [
            {
                "id": seat.id,
                "row": seat.seat_row,
                "number": seat.seat_number,
                "category": seat.category,
                "booked": seat.id in booked_seat_ids,
            }
            for seat in seats
        ],
    }


##############################################################################################
#                                      6 - ПОДТВЕРЖДЕНИЕ БРОНИРОВАНИЯ
# ____________________________________________________________________________________________
@router.post("/api/user/bookings")
async def create_user_booking(
    data: BookingCreateData,
    current_user=Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    if not data.seat_ids:
        raise HTTPException(status_code=400, detail="Не выбраны места")

    session = await db.get(MovieSession, data.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Сеанс не найден")

    seat_ids = sorted(set(data.seat_ids))

    hall_seats = (
        await db.execute(
            select(HallSeat)
            .where(HallSeat.hall_id == session.hall_id)
            .where(HallSeat.id.in_(seat_ids))
        )
    ).scalars().all()

    if len(hall_seats) != len(seat_ids):
        raise HTTPException(status_code=400, detail="Некоторые места не относятся к этому залу")

    already_booked = (
        await db.execute(
            select(ReservationSeat.seat_id)
            .where(ReservationSeat.session_id == data.session_id)
            .where(ReservationSeat.seat_id.in_(seat_ids))
        )
    ).scalars().all()

    if already_booked:
        raise HTTPException(status_code=409, detail="Некоторые места уже заняты")

    reservation = Reservation(
        user_id=current_user.get("user_id"),
        session_id=data.session_id,
    )
    db.add(reservation)
    await db.flush()

    total_price = 0
    for seat in hall_seats:
        final_price = category_price(seat.category, session.base_price)
        total_price += final_price
        db.add(
            ReservationSeat(
                reservation_id=reservation.id,
                session_id=data.session_id,
                seat_id=seat.id,
                final_price=final_price,
            )
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Места уже заняты")

    return {
        "reservation_id": reservation.id,
        "session_id": data.session_id,
        "seat_ids": seat_ids,
        "total_price": total_price,
    }


##############################################################################################
#                                      7 - ЛИЧНЫЙ КАБИНЕТ
# ____________________________________________________________________________________________
@router.get("/api/user/me")
async def user_me(
    current_user=Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(Registered_users, current_user.get("user_id"))
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "id": user.id,
        "name": user.name_user,
        "surname": user.surname_user,
        "email": user.email_user,
    }


@router.get("/api/user/bookings")
async def user_bookings(
    current_user=Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.get("user_id")

    reservations = (
        await db.execute(
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .order_by(Reservation.id.desc())
        )
    ).scalars().all()

    if not reservations:
        return {"bookings": []}

    reservation_ids = [r.id for r in reservations]
    session_ids = list({r.session_id for r in reservations})

    sessions = (
        await db.execute(select(MovieSession).where(MovieSession.id.in_(session_ids)))
    ).scalars().all()
    session_by_id = {s.id: s for s in sessions}

    movie_ids = list({s.movie_id for s in sessions})
    hall_ids = list({s.hall_id for s in sessions})

    movies = (
        await db.execute(select(Movies).where(Movies.id.in_(movie_ids)))
    ).scalars().all() if movie_ids else []
    halls = (
        await db.execute(select(CinemaHall).where(CinemaHall.id.in_(hall_ids)))
    ).scalars().all() if hall_ids else []

    movie_name_by_id = {m.id: m.name for m in movies}
    hall_name_by_id = {h.id: h.name_hall for h in halls}

    reservation_seats = (
        await db.execute(
            select(ReservationSeat)
            .where(ReservationSeat.reservation_id.in_(reservation_ids))
            .order_by(ReservationSeat.id.asc())
        )
    ).scalars().all()

    seat_ids = list({item.seat_id for item in reservation_seats})
    seats = (
        await db.execute(select(HallSeat).where(HallSeat.id.in_(seat_ids)))
    ).scalars().all() if seat_ids else []
    seat_by_id = {s.id: s for s in seats}

    seats_by_reservation: dict[int, list[dict]] = {}
    for item in reservation_seats:
        seat = seat_by_id.get(item.seat_id)
        if item.reservation_id not in seats_by_reservation:
            seats_by_reservation[item.reservation_id] = []
        seats_by_reservation[item.reservation_id].append(
            {
                "row": seat.seat_row if seat else None,
                "number": seat.seat_number if seat else None,
                "final_price": item.final_price,
            }
        )

    result = []
    for reservation in reservations:
        session = session_by_id.get(reservation.session_id)
        booking_seats = seats_by_reservation.get(reservation.id, [])
        total_price = sum(s["final_price"] for s in booking_seats)

        result.append(
            {
                "reservation_id": reservation.id,
                "session_id": reservation.session_id,
                "starts_at": session.starts_at.isoformat() if session else None,
                "movie_name": movie_name_by_id.get(session.movie_id) if session else None,
                "hall_name": hall_name_by_id.get(session.hall_id) if session else None,
                "seats": booking_seats,
                "total_price": total_price,
            }
        )

    return {"bookings": result}


@router.put("/api/user/settings")
async def user_settings_update(
    data: UserSettingsUpdateData,
    current_user=Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(Registered_users, current_user.get("user_id"))
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if data.email is None and data.new_password is None:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    if data.email is not None and data.email != user.email_user:
        existing = (
            await db.execute(
                select(Registered_users).where(Registered_users.email_user == data.email)
            )
        ).scalar_one_or_none()
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Email уже используется")
        user.email_user = data.email

    if data.new_password is not None:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Введите текущий пароль")
        if not verify_password(data.current_password, user.password_user):
            raise HTTPException(status_code=400, detail="Текущий пароль неверный")
        user.password_user = hash_password(data.new_password)

    await db.commit()
    await db.refresh(user)

    token = create_access_token_user(
        {
            "sub": user.email_user,
            "role": "user",
            "user_id": user.id,
        }
    )

    return {
        "message": "Настройки обновлены",
        "access_token": token,
        "user": {
            "name": user.name_user,
            "surname": user.surname_user,
            "email": user.email_user,
        },
    }


@router.delete("/api/user/bookings/{reservation_id}")
async def cancel_user_booking(
    reservation_id: int,
    current_user=Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    reservation = await db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    if reservation.user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Нет доступа к этому бронированию")

    await db.execute(
        delete(ReservationSeat).where(
            ReservationSeat.reservation_id == reservation_id
        )
    )
    await db.execute(delete(Reservation).where(Reservation.id == reservation_id))
    await db.commit()

    return {"message": "Бронирование отменено"}
