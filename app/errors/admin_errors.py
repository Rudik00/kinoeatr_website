from fastapi.responses import JSONResponse


def handle_admin_login_errors(code: str) -> JSONResponse:
    messages = {
        "ADMIN_LOGIN_EMAIL_EMPTY":    "Строка email не может быть пустой",
        "ADMIN_LOGIN_EMAIL_INVALID":  "Неверный email или пароль",
        "ADMIN_LOGIN_PASSWORD_EMPTY": "Пароль не может быть пустым или меньше 8 символов",
        "ADMIN_LOGIN_NO_EMAIL": "Неверный email или пароль",
        "ADMIN_LOGIN_PASSWORD_INVALID": "Неверный email или пароль",
    }

    text = messages[code]

    return JSONResponse(status_code=422, content={"detail": text})


def handle_hall_create_errors(code: str) -> JSONResponse:
    messages = {
        "HALL_NAME_EMPTY": "Название зала не может быть пустым",
        "HALL_SEAT_ROWS_INVALID": "Неверное количество рядов",
        "HALL_SEAT_NUMBERS_PER_ROW_INVALID": "Неверное количество мест в ряду",
        "HALL_NAME_EXISTS": "Зал с таким названием уже существует",
    }
    text = messages[code]
    return JSONResponse(status_code=422, content={"detail": text})
