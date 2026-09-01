"""
Конфигурация бота. Все секреты и параметры окружения читаются из .env
Не хранить токены/ID в коде.
"""
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

_DEFAULT_DB_PATH = BASE_DIR / "fin_faculty_bot.db"


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Переменная окружения {name} не задана. "
            f"Проверьте файл .env (см. .env.example)."
        )
    return value


def _parse_int_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                result.append(int(part))
            except ValueError:
                pass
    return result


def _resolve_database_url(url: str) -> str:
    relative_prefix = "sqlite+aiosqlite:///./"
    if url.startswith(relative_prefix):
        db_name = url[len(relative_prefix) :]
        return f"sqlite+aiosqlite:///{BASE_DIR / db_name}"
    return url


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: _get_env("BOT_TOKEN", required=True))
    database_url: str = field(
        default_factory=lambda: _resolve_database_url(
            _get_env(
                "DATABASE_URL",
                f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}",
            )
        )
    )
    work_group_id: int = field(
        default_factory=lambda: int(_get_env("WORK_GROUP_ID", required=True))
    )
    # ID темы (message_thread_id) в рабочей супергруппе. Если не задан,
    # обращения отправляются в общую тему группы.
    work_group_thread_id: int | None = field(
        default_factory=lambda: (
            int(value) if (value := os.getenv("WORK_GROUP_THREAD_ID")) else None
        )
    )
    # Начальный администратор(ы) — можно указать несколько ID через запятую.
    initial_admin_ids: list[int] = field(
        default_factory=lambda: _parse_int_list(os.getenv("INITIAL_ADMIN_ID"))
    )
    # Если SUPERADMIN_ID не задан, прежний INITIAL_ADMIN_ID получает права
    # суперадмина для обратной совместимости с уже установленным ботом.
    superadmin_ids: list[int] = field(
        default_factory=lambda: (
            _parse_int_list(os.getenv("SUPERADMIN_ID"))
            or _parse_int_list(os.getenv("INITIAL_ADMIN_ID"))
        )
    )
    # Директория для временного хранения загружаемых файлов не нужна —
    # PDF храним по file_id Telegram (см. README, раздел "Хранение файлов").
    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))


settings = Settings()
