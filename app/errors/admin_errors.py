from fastapi.responses import JSONResponse


def handle_admin_register_errors(code: str) -> JSONResponse:
    # разбираем конкретно что случилось у админа
    messages = {
        "ADMIN_REGISTER_EMAIL_EMPTY":    "Введите email",
        "ADMIN_REGISTER_EMAIL_INVALID":  "Некорректный email адрес",
        "ADMIN_REGISTER_PASSWORD_EMPTY": "Введите пароль",
        "ADMIN_REGISTER_PASSWORD_INVALID": "Некорректный пароль",
    }
    text = messages.get(code, "Ошибка регистрации админа")
    return JSONResponse(status_code=422, content={"detail": text})


def handle_admin_login_errors(code: str) -> JSONResponse:
    messages = {
        "ADMIN_LOGIN_EMAIL_EMPTY":    "Строка email не может быть пустой",
        "ADMIN_LOGIN_EMAIL_INVALID":  "Некорректный email адрес",
        "ADMIN_LOGIN_PASSWORD_EMPTY": "Пароль не может быть пустым или меньше 8 символов",
        "ADMIN_LOGIN_NO_EMAIL": "Админ с таким email не найден",
        "ADMIN_LOGIN_PASSWORD_INVALID": "Неверный пароль",
    }

    text = messages[code]

    return JSONResponse(status_code=422, content={"detail": text})
