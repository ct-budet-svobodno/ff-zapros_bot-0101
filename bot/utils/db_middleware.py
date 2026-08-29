"""
Middleware, открывающий сессию SQLAlchemy на каждый апдейт и передающий её
в хендлеры как аргумент `session` (через DI aiogram — параметр с таким
именем автоматически подставляется, т.к. мы кладём его в data).
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.engine import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)
