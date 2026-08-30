"""Команда /ids для получения ID пользователя, чата и forum-темы."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="ids")


def ids_message_text(message: Message) -> str:
    """Сформировать ID текущего пользователя, чата и forum-темы."""
    user_id = message.from_user.id if message.from_user else "недоступен"
    thread_id = message.message_thread_id
    thread_value = str(thread_id) if thread_id is not None else "нет (общая тема или личный чат)"
    chat_type = getattr(message.chat.type, "value", message.chat.type)

    return (
        "🆔 <b>ID текущего сообщения</b>\n\n"
        f"USER_ID: <code>{user_id}</code>\n"
        f"WORK_GROUP_ID: <code>{message.chat.id}</code>\n"
        f"WORK_GROUP_THREAD_ID: <code>{thread_value}</code>\n"
        f"CHAT_TYPE: <code>{chat_type}</code>"
    )


@router.message(Command("ids"))
async def cmd_ids(message: Message) -> None:
    await message.answer(ids_message_text(message))
