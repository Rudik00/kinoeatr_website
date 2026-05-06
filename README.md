# Kinoeatr Website

Веб-приложение кинотеатра на FastAPI + PostgreSQL с двумя отдельными зонами:
- Админка: управление залами, фильмами, сеансами, просмотром бронирований
- Пользовательская часть: просмотр фильмов, выбор мест, регистрация/вход, бронирование, личный кабинет

## Стек
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Pydantic
- JWT (python-jose)
- Passlib (bcrypt)
- Статический frontend на HTML/CSS/JS

## Структура проекта
- app/: backend (роуты, модели, auth, конфигурация БД)
- database/: вспомогательные артефакты БД
- frontend/: статические HTML/CSS/JS страницы админки и пользователей
- main_project.py: точка запуска локального сервера

## Что уже реализовано

### Пользовательский flow
- Список фильмов: /movies
- Детали фильма и расписание: /movie/{movie_id}
- Выбор мест в зале: /session/{session_id}
- Страница подтверждения: /booking?session={id}&seats={id,id}
- Регистрация/вход пользователей: /login
- Личный кабинет: /profile
- В личном кабинете:
	- вкладка Личный кабинет (профиль + список своих бронирований)
	- вкладка Настройки (изменение email, телефона, пароля)

### Админский flow
- Вход в админку: /admin/login
- Панель управления: /admin/dashboard
- Управление залами, фильмами, сеансами, бронированиями

### API (основные пользовательские)
- GET /api/movies
- GET /api/movies/{movie_id}
- GET /api/sessions/{session_id}
- POST /api/user/register
- POST /api/user/login
- GET /api/check-auth
- GET /api/user/me
- GET /api/user/bookings
- PUT /api/user/settings
- POST /api/user/bookings

## Переменные окружения
Создайте файл .env в корне проекта:

SECRET_KEY=your_secret_key
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cinema_db

## Установка и запуск

1. Создайте и активируйте виртуальное окружение

macOS/Linux:
python3 -m venv venv
source venv/bin/activate

Windows (PowerShell):
python -m venv venv
venv\Scripts\Activate.ps1

2. Установите зависимости

pip install -r requirements.txt

3. Запустите сервер

python main_project.py

Сервер будет доступен по адресу:
- http://127.0.0.1:8000

## Примечания по текущему состоянию
- Это уже рабочий MVP, которым можно пользоваться.
- Для продакшн-готовности рекомендуется добавить:
	- миграции БД (Alembic)
	- автоматические тесты (backend + e2e)
	- отмену/возврат бронирований пользователем
	- логирование и мониторинг ошибок
	- rate limit на auth-эндпоинты

## Лицензия
Добавьте нужную лицензию при публикации проекта.
