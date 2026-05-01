from fastapi.responses import JSONResponse


def handle_admin_login_errors(code: str) -> JSONResponse:
    messages = {
        "ADMIN_LOGIN_EMAIL_EMPTY":    "Строка email не может быть пустой",
        "ADMIN_LOGIN_EMAIL_INVALID":  "Неверный email или пароль",
        "ADMIN_LOGIN_PASSWORD_EMPTY": "Пароль не может быть пустым или меньше 8 символов",
        "ADMIN_LOGIN_NO_EMAIL": "Неверный email или пароль",
        "ADMIN_LOGIN_PASSWORD_INVALID": "Неверный email или пароль",
        "ADMIN_INVALID_TOKEN": "Неверный токен доступа",
    }

    text = messages[code]

    return JSONResponse(status_code=422, content={"detail": text})


def handle_hall_create_errors(code: str) -> JSONResponse:
    messages = {
        "HALL_NAME_EMPTY": "Название зала не может быть пустым",
        "HALL_SEAT_ROWS_INVALID": "Неверное количество рядов",
        "HALL_SEAT_NUMBERS_PER_ROW_INVALID": "Неверное количество мест в ряду",
        "HALL_NAME_EXISTS": "Зал с таким названием уже существует",
        "HALL_NOT_FOUND": "Зал не найден",

    }
    text = messages[code]
    return JSONResponse(status_code=422, content={"detail": text})


def handle_movie_create_errors(code: str) -> JSONResponse:
    messages = {
        "MOVIE_NAME_EMPTY": "Название фильма не может быть пустым",
        "MOVIE_DURATION_INVALID": "Неверная продолжительность фильма",
        "MOVIE_DESCRIPTION_EMPTY": "Описание фильма не может быть пустым",
        "MOVIE_RELEASE_DATE_INVALID": "Неверная дата релиза фильма",
        "MOVIE_PREVIEW_FOTO_EMPTY": "URL превью фотографии не может быть пустым",
        "MOVIE_NOT_FOUND": "Фильм не найден",
        "MOVIE_DELETE_HAS_SESSIONS": "Нельзя удалить фильм: для него уже создан сеанс."

    }
    text = messages[code]
    return JSONResponse(status_code=422, content={"detail": text})


def handle_session_create_errors(code: str) -> JSONResponse:
    messages = {
        "SESSION_MOVIE_ID_INVALID": "Неверный ID фильма",
        "SESSION_HALL_ID_INVALID": "Неверный ID зала",
        "SESSION_START_TIME_INVALID": "Неверное время начала сеанса",
        "SESSION_CONFLICT": "Сеанс конфликтует с уже существующим сеансом в этом зале",
        "SESSION_NOT_FOUND": "Сеанс не найден",
    }
    text = messages[code]
    return JSONResponse(status_code=422, content={"detail": text})
