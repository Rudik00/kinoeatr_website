"""
Конфигурация логирования для приложения КиноЗал.

Создаёт два файла в директории logs/:
  - app.log    — все события уровня INFO и выше (запросы, старт, предупреждения)
  - errors.log — только события уровня ERROR и выше (исключения, критические ошибки)

Ротация файлов: каждый файл не превышает 5 МБ, хранится до 5 архивов.
"""

import logging
import logging.handlers
import os


LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
APP_LOG  = os.path.join(LOG_DIR, "app.log")
ERR_LOG  = os.path.join(LOG_DIR, "errors.log")

LOG_FORMAT = (
    "\n"
    "==================== LOG ENTRY ====================\n"
    "%(asctime)s  [%(levelname)-8s]  %(name)s\n"
    "---------------------------------------------------\n"
    "%(message)s\n"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_BYTES   = 5 * 1024 * 1024   # 5 МБ
BACKUP_COUNT = 5


def setup_logging(level: int = logging.INFO) -> None:
    """Инициализирует глобальную конфигурацию логирования.

    Вызывать один раз при старте приложения (в lifespan FastAPI).
    """

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── Хендлер: все INFO+ → logs/app.log ──────────────────────────────────
    app_handler = logging.handlers.RotatingFileHandler(
        APP_LOG,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    # ── Хендлер: только ERROR+ → logs/errors.log ───────────────────────────
    err_handler = logging.handlers.RotatingFileHandler(
        ERR_LOG,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(formatter)

    # ── Хендлер: INFO+ → консоль (удобно при разработке) ───────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ── Корневой логгер ─────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)

    # Убираем все существующие file-хендлеры нашего логгера, чтобы не дублировать
    # (uvicorn с reload=True может вызвать setup_logging повторно)
    kinoeatr_logger = logging.getLogger("kinoeatr")
    kinoeatr_logger.handlers.clear()
    kinoeatr_logger.propagate = False
    kinoeatr_logger.setLevel(level)
    kinoeatr_logger.addHandler(app_handler)
    kinoeatr_logger.addHandler(err_handler)
    kinoeatr_logger.addHandler(console_handler)

    # Заглушить шумные библиотеки
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
