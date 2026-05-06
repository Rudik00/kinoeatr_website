from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()
# ____________________________________________________________________________________
#                                    Админка


# Отдельная таблица для сотрудников/администраторов.
# Не смешивается с обычными пользователями.
class Admins(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    email_admin = Column(String, nullable=False)
    password_admin = Column(String, nullable=False)
# ____________________________________________________________________________________  
#                                    Пользователи


# Аккаунты пользователей: имя, почта, хешированный пароль.
class Registered_users(Base):
    __tablename__ = "registered_users"
    id = Column(Integer, primary_key=True)
    name_user = Column(String, nullable=False)
    surname_user = Column(String, nullable=False)
    email_user = Column(String, nullable=False)
    password_user = Column(String, nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)


# Одноразовый токен подтверждения email.
# Создаётся при регистрации, удаляется после использования или истечения TTL.
class EmailVerificationToken(Base):
    __tablename__ = "email_verification_token"
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("registered_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
# ___________________________________________________________________________________
#                                   Территория кинотеатра


# Список залов кинотеатра.
class CinemaHall(Base):
    __tablename__ = "cinema_hall"
    id = Column(Integer, primary_key=True)
    name_hall = Column(String, nullable=False, unique=True)


# Все места, которые физически существуют в конкретном зале.
# Место = ряд + номер + зал. Создается один раз при добавлении зала.
# Не зависит от сеанса.
class HallSeat(Base):
    __tablename__ = "hall_seat"
    id = Column(Integer, primary_key=True)
    hall_id = Column(Integer, ForeignKey("cinema_hall.id", ondelete="CASCADE"), nullable=False)
    seat_row = Column(Integer, nullable=False)
    seat_number = Column(Integer, nullable=False)
    category = Column(String, default="standard") # standard, vip, premium

    __table_args__ = (
        UniqueConstraint("hall_id", "seat_row", "seat_number", name="uq_hall_row_number"),
    )
# ___________________________________________________________________________________
#                                   Фильмы и сеансы


# Каталог фильмов
class Movies(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    release_date = Column(String, nullable=False)
    preview_foto = Column(String, nullable=False)


# Конкретный сеанс: какой фильм, в каком зале, в какое время.
# Одна запись = один показ.
class MovieSession(Base):
    __tablename__ = "movie_session"
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    hall_id = Column(Integer, ForeignKey("cinema_hall.id", ondelete="RESTRICT"), nullable=False)
    starts_at = Column(DateTime, nullable=False)
    # Базовая цена билета на этот сеанс
    base_price = Column(Integer, nullable=False)
# ___________________________________________________________________________________
#                                      Бронирование


# Шапка брони: кто бронирует и на какой сеанс.
class Reservation(Base):
    __tablename__ = "reservation"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("registered_users.id", ondelete="SET NULL"), nullable=True)
    guest_name = Column(String, nullable=True)
    guest_email = Column(String, nullable=True)
    session_id = Column(Integer, ForeignKey("movie_session.id", ondelete="CASCADE"), nullable=False)


# Детали брони:
# какие именно места забронированы.
# Каждое место = отдельная строка.
# Здесь стоит уникальный индекс (session_id, seat_id),
# который физически запрещает двойное бронирование одного места на один сеанс.
class ReservationSeat(Base):
    __tablename__ = "reservation_seat"
    id = Column(Integer, primary_key=True)
    reservation_id = Column(Integer, ForeignKey("reservation.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("movie_session.id", ondelete="CASCADE"), nullable=False)
    seat_id = Column(Integer, ForeignKey("hall_seat.id", ondelete="RESTRICT"), nullable=False)
    final_price = Column(Integer, nullable=False) # Цена на момент покупки

    # КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ: одно место в одном сеансе только один раз
    __table_args__ = (
        UniqueConstraint("session_id", "seat_id", name="uq_session_seat_once"),
    )
