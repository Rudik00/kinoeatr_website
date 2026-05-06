"""
Скрипт создания администратора.

Использование:
    python create_admin.py

Вводит email и пароль интерактивно, затем создаёт запись в таблице admins.
"""

import asyncio
import getpass
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.database.madels_db import Admins, Base
from app.utils.security import hash_password


load_dotenv()

# Добавляем корень в путь для импортов из app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Ошибка: переменная DATABASE_URL не задана в .env")
    sys.exit(1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_admin():
    print("=== Создание администратора ===\n")

    email = input("Email: ").strip().lower()
    if not email:
        print("Ошибка: email не может быть пустым.")
        return

    password = getpass.getpass("Пароль: ")
    if len(password) < 6:
        print("Ошибка: пароль должен быть не менее 6 символов.")
        return

    password_confirm = getpass.getpass("Повторите пароль: ")
    if password != password_confirm:
        print("Ошибка: пароли не совпадают.")
        return

    async with AsyncSessionLocal() as session:
        # Проверяем, существует ли уже такой email
        result = await session.execute(
            select(Admins).where(Admins.email_admin == email)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"\nАдминистратор с email '{email}' уже существует.")
            return

        admin = Admins(
            email_admin=email,
            password_admin=hash_password(password),
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        print(f"\nАдминистратор создан (id={admin.id}, email={email})")


asyncio.run(create_admin())
