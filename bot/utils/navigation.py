"""Переходы между текстовыми меню и карточками с фотографиями."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup


async def show_text_screen(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    **kwargs,
) -> Message:
    """Редактировать текст или заменить медиакарточку новым меню.

    Новое сообщение отправляется до удаления старого, чтобы при ошибке
    отправки пользователь не остался без экрана и кнопок навигации.
    """
    if message.text is not None and not isinstance(reply_markup, ReplyKeyboardMarkup):
        try:
            return await message.edit_text(text, reply_markup=reply_markup, **kwargs)
        except TelegramBadRequest as exc:
            error = exc.message.lower()
            if "message is not modified" in error:
                return message
            if not any(reason in error for reason in (
                "message can't be edited",
                "message to edit not found",
                "there is no text in the message to edit",
            )):
                raise

    new_message = await message.answer(text, reply_markup=reply_markup, **kwargs)
    try:
        await message.delete()
    except TelegramBadRequest as exc:
        # Даже если старое сообщение уже удалено или слишком старое для
        # удаления, новое меню остаётся доступным.
        if not any(reason in exc.message.lower() for reason in (
            "message can't be deleted",
            "message to delete not found",
        )):
            raise
    return new_message
