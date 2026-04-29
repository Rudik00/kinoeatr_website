from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.errors.admin_errors import (
    handle_admin_register_errors,
    handle_admin_login_errors,
    )

app = FastAPI(title="Cinema Reservation API")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        # достаем наш код из msg (Pydantic добавляет "Value error, " в начало)
        code = error.get("msg", "").replace("Value error, ", "")

        if code.startswith("ADMIN_REGISTER_"):
            return handle_admin_register_errors(code)

        if code.startswith("ADMIN_LOGIN_"):
            return handle_admin_login_errors(code)

        # сюда потом добавишь:
        # if code.startswith("ADMIN_HALL_"): ...
        # if code.startswith("USER_LOGIN_"): ...

    return JSONResponse(status_code=422, content={"detail": "Ошибка валидации"})
