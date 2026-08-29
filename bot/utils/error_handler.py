"""
Глобальный обработчик ошибок (ТЗ, раздел 36): пользователь должен получать
человеческое сообщение, а не traceback. Все исключения логируются.

`bot` внедряется aiogram'ом автоматически из workflow_data (мы передаём bot
в dispatcher.start_polling(bot), поэтому он доступен в любом хендлере,
включая обработчик ошибок).
"""
import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router(name="error_handler")

USER_ERROR_TEXT = (
    "⚠️ Произошла непредвиденная ошибка. Мы уже знаем о проблеме.\n"
    "Пожалуйста, попробуйте ещё раз или начните заново: /menu"
)


@router.errors()
async def handle_errors(event: ErrorEvent, bot: Bot) -> bool:
    logger.exception("Необработанная ошибка при обработке апдейта", exc_info=event.exception)

    update = event.update
    chat_id = None
    if update.message:
        chat_id = update.message.chat.id
    elif update.callback_query and update.callback_query.message:
        chat_id = update.callback_query.message.chat.id

    if chat_id is not None:
        try:
            await bot.send_message(chat_id, USER_ERROR_TEXT)
        except TelegramAPIError:
            logger.warning("Не удалось отправить сообщение об ошибке пользователю в чат %s", chat_id)

    return True
