"""
Обработка обращений администраторами прямо в рабочей группе (ТЗ, разделы
23-25). Нажатие «Ответить» первым администратором переводит обращение в
статус IN_PROGRESS и закрепляет его за этим администратором (crud.take_request
делает это атомарно на уровне SQL UPDATE ... WHERE status='NEW', защищая от
реальной гонки при одновременном нажатии — см. database/crud.py).

ВАЖНО (исправление): после того как обращение взято в работу, отвечать и
закрывать его может ТОЛЬКО назначенный администратор. Любой другой
администратор, нажавший «Ответить» или «Закрыть обращение» на уже занятом
обращении, получает предупреждение и не может продолжить — это проверяется
явно по request.admin_id при каждом действии, а не только в момент взятия
в работу.

FSM-состояние ответа хранится в контексте (чат=рабочая группа, user=админ),
поэтому разные администраторы, отвечающие на разные обращения в одной и той
же группе одновременно, не мешают друг другу.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import RequestStatus, User
from keyboards.admin_kb import response_preview_kb
from services.notifications import notify_user_safe, update_group_message_safe
from states.states import AdminReply
from utils.admin_filter import IsAdmin
from utils.callback_data import RequestActionCB, ResponsePreviewCB

router = Router(name="admin_requests")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

ALREADY_TAKEN_TEXT = "🔄 Обращение уже находится в работе у другого администратора."


@router.callback_query(RequestActionCB.filter(F.action == "reply"))
async def cb_reply_start(
    callback: CallbackQuery, callback_data: RequestActionCB, state: FSMContext, session: AsyncSession
) -> None:
    request = await crud.get_request(session, callback_data.request_id)
    if not request:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    admin = await crud.get_admin_by_telegram_id(session, callback.from_user.id)
    if not admin:
        # Права уже проверены фильтром IsAdmin, но на всякий случай подстрахуемся.
        await callback.answer("⛔ У вас нет доступа.", show_alert=True)
        return

    if request.status == RequestStatus.NEW.value:
        taken = await crud.take_request(session, request.id, admin.id)
        if taken is None:
            # Кто-то другой уже успел взять обращение в работу ровно в этот момент.
            await callback.answer(ALREADY_TAKEN_TEXT, show_alert=True)
            request = await crud.get_request(session, callback_data.request_id)
            user = await session.get(User, request.user_id) if request else None
            if request and user:
                await update_group_message_safe(callback.bot, request, user)
            return
        request = taken
        user = await session.get(User, request.user_id)
        await update_group_message_safe(callback.bot, request, user)
        await notify_user_safe(
            callback.bot, user.telegram_id, f"🔄 Ваше обращение #{request.id} взято в работу."
        )
    elif request.status == RequestStatus.CLOSED.value:
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    elif request.admin_id != admin.id:
        # Обращение в работе, но не у этого администратора — отвечать нельзя.
        await callback.answer(ALREADY_TAKEN_TEXT, show_alert=True)
        return
    # else: request.status == IN_PROGRESS и admin_id == текущий администратор —
    # можно отвечать (в том числе повторно, если нужно уточнить ответ).

    await state.set_state(AdminReply.entering_response)
    await state.update_data(request_id=request.id, admin_id=admin.id)
    await callback.message.answer(f"Введите ответ студенту по обращению #{request.id}:")
    await callback.answer()


@router.message(AdminReply.entering_response, F.text)
async def receive_response_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("Ответ не может быть пустым. Введите текст ответа.")
        return
    await state.update_data(response_text=text)
    data = await state.get_data()
    await state.set_state(AdminReply.preview)
    await message.answer(
        f"Предпросмотр ответа по обращению #{data['request_id']}:\n\n{text}",
        reply_markup=response_preview_kb(data["request_id"]),
    )


@router.message(AdminReply.entering_response)
async def receive_response_wrong_type(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте ответ текстом.")


@router.callback_query(AdminReply.preview, ResponsePreviewCB.filter(F.action == "cancel"))
async def response_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отправка ответа отменена.")
    await callback.answer()


@router.callback_query(AdminReply.preview, ResponsePreviewCB.filter(F.action == "send"))
async def response_send(
    callback: CallbackQuery, callback_data: ResponsePreviewCB, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()

    # Повторная проверка "владения" на момент отправки — за время написания
    # ответа обращение теоретически могло быть закрыто или переназначено.
    request = await crud.get_request(session, data["request_id"])
    if not request:
        await state.clear()
        await callback.message.edit_text("⚠️ Обращение не найдено.")
        await callback.answer()
        return
    if request.status == RequestStatus.CLOSED.value:
        await state.clear()
        await callback.message.edit_text(f"⚠️ Обращение #{request.id} уже закрыто, ответ не отправлен.")
        await callback.answer()
        return
    if request.admin_id != data.get("admin_id"):
        await state.clear()
        await callback.message.edit_text(f"⚠️ {ALREADY_TAKEN_TEXT}")
        await callback.answer()
        return

    request = await crud.set_request_response(session, data["request_id"], data["response_text"])
    await state.clear()

    user = await session.get(User, request.user_id)
    await notify_user_safe(
        callback.bot,
        user.telegram_id,
        f"💬 Ответ по вашему обращению #{request.id}:\n\n{request.response_text}",
    )
    await update_group_message_safe(callback.bot, request, user)
    await callback.message.edit_text(f"✅ Ответ по обращению #{request.id} отправлен студенту.")
    await callback.answer()


@router.callback_query(RequestActionCB.filter(F.action == "close"))
async def cb_close(
    callback: CallbackQuery, callback_data: RequestActionCB, session: AsyncSession
) -> None:
    request = await crud.get_request(session, callback_data.request_id)
    if not request:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return
    if request.status == RequestStatus.CLOSED.value:
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    if request.status == RequestStatus.NEW.value:
        await callback.answer("Сначала возьмите обращение в работу («💬 Ответить»).", show_alert=True)
        return

    admin = await crud.get_admin_by_telegram_id(session, callback.from_user.id)
    if not admin or request.admin_id != admin.id:
        await callback.answer(ALREADY_TAKEN_TEXT, show_alert=True)
        return

    request = await crud.close_request(session, request.id)
    user = await session.get(User, request.user_id)
    await notify_user_safe(
        callback.bot,
        user.telegram_id,
        f"✅ Ваше обращение #{request.id} закрыто.\nЗапрос считается удовлетворённым.",
    )
    await update_group_message_safe(callback.bot, request, user)
    await callback.answer("Обращение закрыто")
