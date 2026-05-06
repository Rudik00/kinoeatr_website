# КиноЗал — сайт кинотеатра

Веб-приложение кинотеатра на FastAPI + PostgreSQL с двумя отдельными зонами:
- **Пользовательская часть** — просмотр фильмов, выбор мест, регистрация с подтверждением email, бронирование, личный кабинет
- **Админка** — управление залами, фильмами, сеансами, просмотр бронирований и статистика

---

## Стек технологий

| Слой | Технология |
|---|---|
| Backend | Python 3.11+, FastAPI 0.136 |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| База данных | PostgreSQL |
| Аутентификация | JWT (python-jose 3.5), bcrypt 4 (passlib) |
| Email | smtplib, STARTTLS |
| Логирование | Python `logging`, RotatingFileHandler |
| Валидация | Pydantic v2, email-validator |
| Окружение | python-dotenv |

---

## Структура проекта

```
kinoeatr_website/
├── main_project.py          # точка входа, запуск uvicorn
├── logging_config.py        # настройка логирования
├── requirements.txt
├── .env                     # переменные окружения (не в git)
├── logs/
│   ├── app.log              # все события INFO+ (ротация 5 МБ × 5)
│   └── errors.log           # только ERROR+ (ротация 5 МБ × 5)
├── app/
│   ├── main.py              # FastAPI app, middleware, роуты страниц
│   ├── db.py                # get_db (async session)
│   ├── database/
│   │   ├── madels_db.py     # модели SQLAlchemy
│   │   └── create_db.py     # init_db()
│   ├── routers/
│   │   ├── movies.py        # API пользователя
│   │   └── admin.py         # API администратора
│   ├── utils/
│   │   ├── email.py         # отправка письма-подтверждения
│   │   ├── jwt_token.py     # create/decode токенов user и admin
│   │   └── security.py      # hash_password / verify_password
│   └── errors/
│       └── admin_errors.py  # обработчики ошибок валидации
└── frontend/
    ├── users/
    │   ├── home_page.html   # каталог фильмов
    │   ├── movies.html      # страница фильма
    │   ├── hall.html        # выбор мест
    │   ├── booking.html     # подтверждение бронирования
    │   ├── profile.html     # личный кабинет
    │   └── auth.html        # вход / регистрация
    └── admin/
        ├── admin_login.html
        ├── admin_dashboard.html
        ├── hall/
        ├── movies/
        ├── movie_session/
        └── bookings/
```

---

## Переменные окружения (`.env`)

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cinema_db

# JWT
SECRET_KEY=your-secret-key

# Email (SMTP) — необязательно для локальной разработки
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # пароль приложения Google (16 символов)

# Базовый URL приложения (используется в письме-подтверждении)
APP_BASE_URL=http://localhost:8000
```

> Если `SMTP_USER` / `SMTP_PASSWORD` не заданы, письмо не отправляется, а в ответе регистрации возвращается поле `dev_verify_url` — готовая ссылка для ручной верификации.

---

## Установка и запуск

```bash
# 1. Клонировать и перейти в папку
git clone <repo-url>
cd kinoeatr_website

# 2. Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env (см. раздел выше)

# 5. Применить миграции / создать таблицы
#    Таблицы создаются автоматически при старте через init_db()

# 6. Запустить сервер
python main_project.py
```

Приложение будет доступно по адресу: `http://127.0.0.1:8000`

---

## Схема базы данных (ключевые таблицы)

```sql
-- Пользователи
CREATE TABLE registered_users (
    id              SERIAL PRIMARY KEY,
    name_user       VARCHAR NOT NULL,
    surname_user    VARCHAR NOT NULL,
    email_user      VARCHAR UNIQUE NOT NULL,
    password_user   VARCHAR NOT NULL,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE
);

-- Токены подтверждения email
CREATE TABLE email_verification_token (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER UNIQUE REFERENCES registered_users(id) ON DELETE CASCADE,
    token       VARCHAR UNIQUE NOT NULL,
    expires_at  TIMESTAMP NOT NULL
);
```

---

## API — пользовательская зона

### Аутентификация и профиль

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/user/register` | Регистрация. Отправляет письмо-подтверждение |
| `POST` | `/api/user/login` | Вход. Возвращает JWT. Блокирует неверифицированных |
| `GET` | `/api/user/verify/{token}` | Подтверждение email по токену из письма |
| `GET` | `/api/check-auth` | Проверка валидности текущего токена |
| `GET` | `/api/user/me` | Данные текущего пользователя |
| `PUT` | `/api/user/settings` | Изменение email и/или пароля |

### Фильмы и бронирование

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/movies` | Список всех фильмов |
| `GET` | `/api/movies/{movie_id}` | Детали фильма с сеансами |
| `GET` | `/api/sessions/{session_id}` | Детали сеанса (зал, места, цены) |
| `POST` | `/api/user/bookings` | Создать бронирование |
| `GET` | `/api/user/bookings` | История бронирований пользователя |
| `DELETE` | `/api/user/bookings/{reservation_id}` | Отмена бронирования |

---

## API — административная зона

Все эндпоинты требуют JWT администратора (`Authorization: Bearer <token>`).

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/login` | Вход администратора |
| `GET` | `/api/me` | Данные текущего администратора |
| `GET/POST` | `/api/halls` | Список залов / создать зал |
| `GET/PUT/DELETE` | `/api/halls/{hall_id}` | Получить / изменить / удалить зал |
| `GET/POST` | `/api/movies` | Список фильмов / добавить фильм |
| `PUT/DELETE` | `/api/movies_edit/{movie_id}` | Изменить / удалить фильм |
| `GET/POST` | `/api/sessions` | Список сеансов / создать сеанс |
| `PUT/DELETE` | `/api/sessions_edit/{session_id}` | Изменить / удалить сеанс |
| `GET` | `/api/bookings` | Все бронирования |
| `GET` | `/api/bookings/{session_id}` | Бронирования на сеанс |
| `GET` | `/api/stats` | Общая статистика |

---

## Флоу регистрации

```
POST /api/user/register
    │
    ├─ пользователь уже верифицирован → 409 Conflict
    │
    ├─ пользователь существует, но не верифицирован
    │     → обновляет данные, генерирует новый токен, переотправляет письмо
    │
    └─ новый пользователь
          → создаёт запись (is_verified=False)
          → генерирует токен (TTL 24 ч)
          → отправляет письмо или возвращает dev_verify_url

GET /api/user/verify/{token}
    → устанавливает is_verified=True
    → возвращает HTML с JWT в URL-хэше (#token=...)
    → браузер сохраняет токен в localStorage
```

---

## Логирование

Логи пишутся в директорию `logs/` (файлы не попадают в git).

| Файл | Уровень | Ротация |
|---|---|---|
| `logs/app.log` | INFO и выше | 5 МБ × 5 архивов |
| `logs/errors.log` | ERROR и выше | 5 МБ × 5 архивов |

Middleware автоматически логирует каждый HTTP-запрос: метод, путь, статус-код, время ответа. Запросы с кодом 4xx записываются на уровне WARNING.

---

## Страницы приложения

| URL | Страница |
|---|---|
| `/movies` | Каталог фильмов |
| `/movie/{id}` | Страница фильма |
| `/session/{id}` | Выбор мест в зале |
| `/booking` | Подтверждение бронирования |
| `/profile` | Личный кабинет |
| `/login` | Вход / регистрация |
| `/admin/login` | Вход в админку |
| `/admin/dashboard` | Дашборд администратора |
