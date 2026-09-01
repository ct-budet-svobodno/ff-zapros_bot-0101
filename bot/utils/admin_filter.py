"""
Фильтр проверки прав администратора.

ВАЖНО (см. ТЗ, разделы 4 и 37): проверка выполняется по Telegram user ID
через таблицу admins в БД, а не по username. Фильтр применяется не только
к команде /admin, но и ко ВСЕМ административным хендлерам (команды и
callback), чтобы обычный пользователь не мог вызвать admin-функцию в обход
меню, отправив callback_data вручную.
"""
from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from database.crud import is_admin, is_superadmin
from database.engine import async_session_maker


class IsAdmin(BaseFilter):
    """Пропускает апдейт дальше только если пользователь есть в таблице admins."""

    async def __call__(self, event: Message | CallbackQuery) -> bool | dict[str, Any]:
        user = event.from_user
        if user is None:
            return False
        async with async_session_maker() as session:
            allowed = await is_admin(session, user.id)
        return allowed


class IsSuperAdmin(BaseFilter):
    """Пропускает только администратора с правом управления админами."""

    async def __call__(self, event: Message | CallbackQuery) -> bool | dict[str, Any]:
        user = event.from_user
        if user is None:
            return False
        async with async_session_maker() as session:
            allowed = await is_superadmin(session, user.id)
        return allowed


NOT_ADMIN_TEXT = "⛔ У вас нет доступа к панели администратора."
