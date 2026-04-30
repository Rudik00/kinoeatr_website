from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles


# обработчики ошибок
from .errors.admin_errors import (
    handle_admin_login_errors,
    handle_hall_create_errors,
)

# роутеры
from .routers.admin import router as admin_router

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

# роутеры
app.include_router(admin_router)


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

        if code.startswith("HALL_"):
            return handle_hall_create_errors(code)

    return JSONResponse(
        status_code=422,
        content={"detail": "Ошибка валидации"},
    )


@app.get("/admin/login")
async def login_page():
    return FileResponse("frontend/admin/login.html")


@app.get("/admin/dashboard")
async def dashboard_page():
    return FileResponse("frontend/admin/dashboard.html")


@app.get("/admin/halls")
async def halls_page():
    return FileResponse("frontend/admin/halls/index.html")


@app.get("/admin/halls/create")
async def halls_create_page():
    return FileResponse("frontend/admin/creation_hall/index.html")
