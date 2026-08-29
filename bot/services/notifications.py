"""
Сервис уведомлений: инкапсулирует отправку сообщений студенту и в рабочую
группу, а также единообразную обработку ошибок (пользователь заблокировал
бота, группа недоступна и т.п.) — см. ТЗ, раздел 36 "Логирование и ошибки".
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import settings
from database.models import Request, User
from keyboards.admin_kb import request_group_kb
from utils.formatting import author_label, group_message_text

logger = logging.getLogger(__name__)


async def notify_user_safe(bot: Bot, telegram_id: int, text: str) -> bool:
    """Отправляет сообщение пользователю, не роняя обработчик при ошибке."""
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        return True
    except TelegramAPIError as exc:
        logger.warning("Не удалось отправить сообщение пользователю %s: %s", telegram_id, exc)
        return False


async def publish_request_to_group(bot: Bot, request: Request, user: User) -> tuple[int, int] | None:
    """Публикует новое обращение в рабочей группе. Возвращает (chat_id, message_id)."""
    label = author_label(request, user.username, user.full_name)
    text = group_message_text(request, label)
    try:
        message = await bot.send_message(
            chat_id=settings.work_group_id,
            text=text,
            reply_markup=request_group_kb(request.id, request.status),
        )
        return message.chat.id, message.message_id
    except TelegramAPIError as exc:
        logger.error("Не удалось опубликовать обращение #%s в рабочей группе: %s", request.id, exc)
        return None


async def update_group_message_safe(bot: Bot, request: Request, user: User) -> None:
    """Обновляет текст/клавиатуру сообщения в группе после смены статуса."""
    if not request.group_chat_id or not request.group_message_id:
        return
    label = author_label(request, user.username, user.full_name)
    text = group_message_text(request, label)
    try:
        await bot.edit_message_text(
            chat_id=request.group_chat_id,
            message_id=request.group_message_id,
            text=text,
            reply_markup=request_group_kb(request.id, request.status),
        )
    except TelegramAPIError as exc:
        logger.warning("Не удалось обновить сообщение обращения #%s в группе: %s", request.id, exc)
