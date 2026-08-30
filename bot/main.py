"""
Точка входа. Порядок регистрации роутеров важен:
  1. error_handler — ловит исключения из всех остальных роутеров;
  2. admin-роутеры (защищены фильтром IsAdmin) — идут раньше user-роутеров,
     чтобы админские callback'и (например, обработка обращений в группе)
     перехватывались точно;
  3. пользовательские и общие роутеры;
  4. fallback — обязательно последним, ловит всё необработанное.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from config import settings
from database.engine import init_db
from database.seed import run_seed
from handlers.admin import admins as admin_admins
from handlers.admin import content as admin_content
from handlers.admin import digests as admin_digests
from handlers.admin import documents as admin_documents
from handlers.admin import faculty_admins as admin_faculty_admins
from handlers.admin import leaders as admin_leaders
from handlers.admin import organizations as admin_organizations
from handlers.admin import panel as admin_panel
from handlers.admin import requests as admin_requests
from handlers import ids
from handlers.requests import user_request
from handlers.user import about as user_about
from handlers.user import council as user_council
from handlers.user import documentation as user_documentation
from handlers.user import fallback as user_fallback
from handlers.user import start as user_start
from utils.db_middleware import DbSessionMiddleware
from utils.error_handler import router as error_router


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Библиотеки шумят на DEBUG/INFO — приглушим лишнее.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    private_commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Открыть главное меню"),
        BotCommand(command="admin", description="Открыть админ-панель"),
        BotCommand(command="ids", description="Показать ID чата и темы"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(
        [
            BotCommand(command="ids", description="Показать ID чата и темы"),
        ],
        scope=BotCommandScopeAllGroupChats(),
    )

    # Middleware с сессией БД — на все типы апдейтов.
    dp.update.middleware(DbSessionMiddleware())

    # Роутеры. Порядок важен (см. докстринг модуля).
    dp.include_router(error_router)
    dp.include_router(ids.router)

    dp.include_router(admin_panel.router)
    dp.include_router(admin_content.router)
    dp.include_router(admin_faculty_admins.router)
    dp.include_router(admin_organizations.router)
    dp.include_router(admin_leaders.router)
    dp.include_router(admin_digests.router)
    dp.include_router(admin_documents.router)
    dp.include_router(admin_requests.router)
    dp.include_router(admin_admins.router)

    dp.include_router(user_start.router)
    dp.include_router(user_about.router)
    dp.include_router(user_council.router)
    dp.include_router(user_documentation.router)
    dp.include_router(user_request.router)

    dp.include_router(user_fallback.router)

    logger.info("Инициализация базы данных...")
    await init_db()
    await run_seed()

    logger.info("Бот запускается (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен.")
