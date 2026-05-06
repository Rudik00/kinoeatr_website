import logging
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Добавляем корень проекта в путь для импорта logging_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging  # noqa: E402

from .database.create_db import init_db
from .errors.admin_errors import (
    handle_admin_login_errors,
    handle_hall_create_errors,
    handle_movie_create_errors,
    handle_session_create_errors,
)
from .routers.admin import router as admin_router
from .routers.movies import router as movies_router

logger = logging.getLogger("kinoeatr")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()   # вызывается внутри воркера uvicorn
    logger.info("=== Приложение КиноЗал запущено ===")
    await init_db()
    yield
    logger.info("=== Приложение КиноЗал остановлено ===")


app = FastAPI(title="Cinema Reservation API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "Необработанное исключение: %s %s — %s",
            request.method, request.url.path, exc,
            exc_info=True,
        )
        raise
    elapsed = (time.perf_counter() - start) * 1000
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(
        level,
        "%s %s → %s  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response

# статические файлы (фронтенд)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# роутеры для админа
app.include_router(admin_router)

# роуты для пользователей
app.include_router(movies_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    logger.warning(
        "Ошибка валидации: %s %s — %s",
        request.method, request.url.path, exc.errors(),
    )
    for error in exc.errors():
        # достаем наш код из msg (Pydantic добавляет "Value error, " в начало)
        code = error.get("msg", "").replace("Value error, ", "")

        if code.startswith("ADMIN_LOGIN_"):
            return handle_admin_login_errors(code)

        if code.startswith("ADMIN_HALL_"):
            return handle_hall_create_errors(code)

        if code.startswith("ADMIN_MOVIE_"):
            return handle_movie_create_errors(code)

        if code.startswith("ADMIN_SESSION_"):
            return handle_session_create_errors(code)

    return JSONResponse(
        status_code=422,
        content={"detail": "Ошибка валидации"},
    )


################################################################
#                                       РОУТЫ ДЛЯ АДМИНА
@app.get("/admin/login")
async def login_page():
    return FileResponse("frontend/admin/admin_login.html")


@app.get("/admin/dashboard")
async def dashboard_page():
    return FileResponse("frontend/admin/admin_dashboard.html")


@app.get("/admin/halls")
async def halls_page():
    return FileResponse("frontend/admin/hall/output_halls.html")


@app.get("/admin/halls/create")
async def halls_create_page():
    return FileResponse("frontend/admin/hall/creation_hall.html")


@app.get("/admin/halls/edit")
async def halls_edit_page():
    return FileResponse("frontend/admin/hall/edit_hall.html")


@app.get("/admin/movies")
async def movies_page():
    return FileResponse("frontend/admin/movies/output_movies.html")


@app.get("/admin/movies/create")
async def movies_create_page():
    return FileResponse("frontend/admin/movies/creation_movies.html")


@app.get("/admin/movies/edit")
async def movies_edit_page():
    return FileResponse("frontend/admin/movies/edit_movies.html")


@app.get("/admin/sessions")
async def sessions_page():
    return FileResponse(
        "frontend/admin/movie_session/output_movie_session.html"
    )


@app.get("/admin/sessions/create")
async def sessions_create_page():
    return FileResponse(
        "frontend/admin/movie_session/creation_movie_session.html"
    )


@app.get("/admin/sessions/edit")
async def sessions_edit_page():
    return FileResponse(
        "frontend/admin/movie_session/edit_movie_session.html"
    )


@app.get("/admin/bookings")
async def bookings_page():
    return FileResponse("frontend/admin/bookings/bookings.html")


@app.get("/admin/bookings/{session_id}")
async def booking_detail_page(session_id: int):
    return FileResponse("frontend/admin/bookings/booking_session.html")


################################################################
#                                      РОУТЫ ДЛЯ ПОЛЬЗОВАТЕЛЯ
@app.get("/movies")
async def home_page():
    return FileResponse("frontend/users/home_page.html")


@app.get("/movie/{movie_id}")
async def movie_detail(movie_id: int):
    return FileResponse("frontend/users/movies.html")


@app.get("/session/{session_id}")
async def session_hall(session_id: int):
    return FileResponse("frontend/users/hall.html")


@app.get("/booking")
async def booking_page():
    return FileResponse("frontend/users/booking.html")


@app.get("/profile")
async def profile_page():
    return FileResponse("frontend/users/profile.html")


@app.get("/login")
async def user_login_page():
    return FileResponse("frontend/users/auth.html")
