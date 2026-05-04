from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles


# обработчики ошибок
from .errors.admin_errors import (
    handle_admin_login_errors,
    handle_hall_create_errors,
    handle_movie_create_errors,
    handle_session_create_errors,
)

# роутеры
from .routers.admin import router as admin_router
from .routers.movies import router as movies_router

# база данных
from .database.create_db import init_db
from contextlib import asynccontextmanager


# при запуске приложения выполняется init_db,
# который создает таблицы в базе данных,
# если их нет
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # выполняется один раз при запуске
    yield


app = FastAPI(title="Cinema Reservation API", lifespan=lifespan)

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
