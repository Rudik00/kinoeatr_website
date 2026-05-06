"""
Отправка email через SMTP.

Использует встроенный smtplib + asyncio.to_thread (без внешних зависимостей).
Настройки берутся из .env:

    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your@gmail.com
    SMTP_PASSWORD=app_password_here
    APP_BASE_URL=http://127.0.0.1:8000
"""

import asyncio
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("kinoeatr.email")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")


def build_verification_url(token: str) -> str:
    return f"{APP_BASE_URL}/api/user/verify/{token}"


def smtp_is_configured() -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    if SMTP_USER == "your@gmail.com":
        return False
    if SMTP_PASSWORD == "your_app_password_here":
        return False
    return True


def _build_verification_email(to_email: str, token: str) -> MIMEMultipart:
    verify_url = build_verification_url(token)

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #c0392b;">КиноЗал — подтверждение email</h2>
        <p>Для завершения регистрации нажмите кнопку ниже:</p>
        <a href="{verify_url}"
           style="display:inline-block; padding:12px 24px; background:#c0392b;
                  color:#fff; text-decoration:none; border-radius:6px; font-size:15px;">
          Подтвердить email
        </a>
        <p style="color:#888; font-size:12px; margin-top:24px;">
          Ссылка действительна 24 часа. Если вы не регистрировались — просто
          проигнорируйте это письмо.
        </p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "КиноЗал — подтвердите вашу почту"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def _send_sync(to_email: str, token: str) -> None:
    """Синхронная отправка (запускается в потоке через asyncio.to_thread)."""
    if not smtp_is_configured():
        raise RuntimeError("SMTP не настроен: заполните SMTP_USER/SMTP_PASSWORD в .env")

    msg = _build_verification_email(to_email, token)
    context = ssl.create_default_context()

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

    logger.info("Письмо подтверждения отправлено на %s", to_email)


async def send_verification_email(to_email: str, token: str) -> tuple[bool, str | None]:
    """Асинхронная отправка email.

    Returns:
        (True, None) на успешную отправку.
        (False, reason) если отправка не удалась.
    """
    try:
        await asyncio.to_thread(_send_sync, to_email, token)
        return True, None
    except Exception as exc:
        logger.error("Не удалось отправить письмо на %s: %s", to_email, exc)
        return False, str(exc)
