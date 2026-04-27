from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# movies — фильмы
# cinema_hall — залы
# hall_seat — места в зале
# movie_session — сеансы
# registered_users — зарегистрированные пользователи
# admins — администраторы
# reservation — бронь (шапка)
# reservation_seat — конкретные места в брони

# Каталог фильмов
class Movies(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    show_date = Column(String, nullable=False)
    show_time = Column(String, nullable=False)
    description = Column(String, nullable=False)
    release_date = Column(String, nullable=False)
    preview_foto = Column(String, nullable=False)


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

    __table_args__ = (
        UniqueConstraint("hall_id", "seat_row", "seat_number", name="uq_hall_row_number"),
    )


# Конкретный сеанс: какой фильм, в каком зале, в какое время.
# Одна запись = один показ.
class MovieSession(Base):
    __tablename__ = "movie_session"
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    hall_id = Column(Integer, ForeignKey("cinema_hall.id", ondelete="RESTRICT"), nullable=False)
    starts_at = Column(DateTime, nullable=False)


# Аккаунты пользователей: имя, почта, телефон, хешированный пароль.
class Registered_users(Base):
    __tablename__ = "registered_users"
    id = Column(Integer, primary_key=True)
    name_user = Column(String, nullable=False)
    surname_user = Column(String, nullable=False)
    email_user = Column(String, nullable=False)
    number_telephone_user = Column(String, nullable=False)
    password_user = Column(String, nullable=False)


# Отдельная таблица для сотрудников/администраторов.
# Не смешивается с обычными пользователями.
class Admins(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    name_admin = Column(String, nullable=False)
    surname_admin = Column(String, nullable=False)
    email_admin = Column(String, nullable=False)
    password_admin = Column(String, nullable=False)


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

    # КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ: одно место в одном сеансе только один раз
    __table_args__ = (
        UniqueConstraint("session_id", "seat_id", name="uq_session_seat_once"),
    )
