"""Совместная обработка обращений администраторами в рабочей Telegram-теме.

Администратор отвечает на карточку обращения нативным Telegram Reply. Бот создаёт
предпросмотр с кнопками подтверждения в той же теме. Каждый ответ хранится
отдельно; эксклюзивного «владельца» обращения нет.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import crud
from database.models import Request, RequestResponseStatus, RequestStatus, User
from keyboards.admin_kb import response_preview_kb
from services.notifications import notify_user_safe, update_group_message_safe
from utils.admin_filter import IsAdmin
from utils.callback_data import RequestActionCB, ResponseActionCB
from utils.formatting import escape_html

router = Router(name="admin_requests")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MAX_RESPONSE_LENGTH = 3500
REPLY_HELP_TEXT = (
    "Используйте обычную функцию Telegram «Reply / Ответить» "
    "на само сообщение с обращением, затем напишите текст. "
    "Бот покажет предпросмотр перед отправкой студенту."
)


class RequestMessageReplyFilter(BaseFilter):
    """Пропустить только Reply на сохранённую карточку обращения в нужной теме."""

    async def __call__(
        self,
        message: Message,
        session: AsyncSession,
    ) -> bool | dict[str, Any]:
        replied = message.reply_to_message
        if replied is None or message.chat.id != settings.work_group_id:
            return False
        if (
            settings.work_group_thread_id is not None
            and message.message_thread_id != settings.work_group_thread_id
        ):
            return False

        request = await crud.get_request_by_group_message(
            session,
            chat_id=message.chat.id,
            message_id=replied.message_id,
        )
        if request is None:
            return False
        return {"request": request}


def _preview_text(request_id: int, response_text: str, retry: bool = False) -> str:
    title = "⚠️ <b>Ответ не доставлен</b>" if retry else "📝 <b>Предпросмотр ответа</b>"
    hint = (
        "Telegram отклонил отправку. Проверьте логи и повторите."
        if retry
        else "Проверьте текст и подтвердите отправку."
    )
    return (
        f"{title}\n"
        f"Обращение: <b>#{request_id}</b>\n\n"
        f"{escape_html(response_text)}\n\n"
        f"{hint}"
    )


@router.callback_query(RequestActionCB.filter(F.action == "reply"))
async def cb_reply_help(callback: CallbackQuery) -> None:
    # Поддерживает и новую кнопку, и старые карточки с кнопкой «Ответить».
    await callback.answer(REPLY_HELP_TEXT, show_alert=True)


@router.message(RequestMessageReplyFilter(), F.text)
async def receive_request_reply(
    message: Message,
    request: Request,
    session: AsyncSession,
) -> None:
    if request.status == RequestStatus.CLOSED.value:
        await message.reply("⚠️ Обращение уже закрыто. Ответ не создан.")
        return

    text = message.text.strip()
    if not text:
        await message.reply("⚠️ Ответ не может быть пустым.")
        return
    if len(text) > MAX_RESPONSE_LENGTH:
        await message.reply(
            f"⚠️ Ответ слишком длинный. Максимум — {MAX_RESPONSE_LENGTH} символов."
        )
        return

    admin = await crud.get_admin_by_telegram_id(session, message.from_user.id)
    if admin is None:
        return

    response = await crud.create_response_draft(
        session,
        request_id=request.id,
        admin_id=admin.id,
        text=text,
        source_message_id=message.message_id,
    )
    preview = await message.reply(
        _preview_text(request.id, text),
        reply_markup=response_preview_kb(response.id),
    )
    await crud.set_response_preview_message(session, response.id, preview.message_id)


@router.message(RequestMessageReplyFilter())
async def receive_request_reply_wrong_type(message: Message) -> None:
    await message.reply("⚠️ Ответ студенту пока можно отправить только текстом.")


@router.callback_query(ResponseActionCB.filter(F.action == "cancel"))
async def response_cancel(
    callback: CallbackQuery,
    callback_data: ResponseActionCB,
    session: AsyncSession,
) -> None:
    admin = await crud.get_admin_by_telegram_id(session, callback.from_user.id)
    if admin is None:
        await callback.answer("⛔ У вас нет доступа.", show_alert=True)
        return

    response = await crud.cancel_response(session, callback_data.response_id, admin.id)
    if response is None:
        await callback.answer(
            "Этот черновик вам не принадлежит или уже обработан.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        f"❌ Черновик ответа по обращению #{response.request_id} отменён."
    )
    await callback.answer()


@router.callback_query(ResponseActionCB.filter(F.action.in_({"send", "retry"})))
async def response_send(
    callback: CallbackQuery,
    callback_data: ResponseActionCB,
    session: AsyncSession,
) -> None:
    admin = await crud.get_admin_by_telegram_id(session, callback.from_user.id)
    response = await crud.get_response(session, callback_data.response_id)
    if admin is None or response is None:
        await callback.answer("Ответ не найден.", show_alert=True)
        return
    if response.admin_id != admin.id:
        await callback.answer("Подтвердить может только автор этого ответа.", show_alert=True)
        return
    if response.status == RequestResponseStatus.SENT.value:
        await callback.answer("Ответ уже доставлен студенту.", show_alert=True)
        return
    if response.status == RequestResponseStatus.CANCELLED.value:
        await callback.answer("Черновик отменён.", show_alert=True)
        return

    request = await crud.get_request(session, response.request_id)
    if request is None or request.status == RequestStatus.CLOSED.value:
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return

    claimed = await crud.claim_response_for_sending(session, response.id, admin.id)
    if claimed is None:
        await callback.answer("Ответ уже обрабатывается.", show_alert=True)
        return

    user = await session.get(User, request.user_id)
    delivered = user is not None and await notify_user_safe(
        callback.bot,
        user.telegram_id,
        f"💬 Ответ на ваше обращение:\n\n{escape_html(claimed.text)}",
    )

    if not delivered:
        await crud.mark_response_failed(session, claimed.id)
        await callback.message.edit_text(
            _preview_text(request.id, claimed.text, retry=True),
            reply_markup=response_preview_kb(claimed.id, retry=True),
        )
        await callback.answer("Ответ не доставлен. Подробности есть в логах.", show_alert=True)
        return

    await crud.mark_response_sent(session, claimed.id)
    request = await crud.get_request(session, request.id)
    response_count = await crud.count_sent_responses(session, request.id)
    await update_group_message_safe(
        callback.bot,
        request,
        user,
        response_count=response_count,
    )

    admin_name = callback.from_user.full_name
    if callback.from_user.username:
        admin_name += f" (@{callback.from_user.username})"
    await callback.message.edit_text(
        f"✅ <b>Ответ #{claimed.id} доставлен студенту</b>\n"
        f"Обращение: <b>#{request.id}</b>\n"
        f"Администратор: {escape_html(admin_name)}\n\n"
        f"{escape_html(claimed.text)}"
    )
    await callback.answer("Ответ доставлен")


@router.callback_query(RequestActionCB.filter(F.action == "close"))
async def cb_close(
    callback: CallbackQuery,
    callback_data: RequestActionCB,
    session: AsyncSession,
) -> None:
    request = await crud.get_request(session, callback_data.request_id)
    if request is None:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if request.status == RequestStatus.CLOSED.value:
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return

    response_count = await crud.count_sent_responses(session, request.id)
    if response_count == 0:
        await callback.answer("Сначала отправьте студенту хотя бы один ответ.", show_alert=True)
        return

    request = await crud.close_request(session, request.id)
    if request is None:
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    user = await session.get(User, request.user_id)
    delivered = user is not None and await notify_user_safe(
        callback.bot,
        user.telegram_id,
        "✅ Ваше обращение закрыто.",
    )
    if user is not None:
        await update_group_message_safe(
            callback.bot,
            request,
            user,
            response_count=response_count,
        )

    if delivered:
        await callback.answer("Обращение закрыто")
    else:
        await callback.answer(
            "Обращение закрыто, но уведомление студенту не доставлено.",
            show_alert=True,
        )
