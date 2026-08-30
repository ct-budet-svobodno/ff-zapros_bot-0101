"""
Сценарий "📨 Задать вопрос":
Анонимно/Не анонимно -> Курс -> Корпус -> Текст -> Предпросмотр -> Отправка.

Важно про анонимность (ТЗ, раздел 16): даже при анонимном обращении
Telegram user_id сохраняется в БД в поле requests.user_id (через таблицу
users), чтобы бот мог доставить ответ автору. "Анонимно" только скрывает
личность от администраторов в тексте, публикуемом в рабочей группе, и не
показывается администратору при ответе.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.common_kb import BTN_ASK, main_menu_kb
from keyboards.user_kb import anonymity_kb, building_kb, course_kb, request_preview_kb
from services.notifications import publish_request_to_group
from states.states import RequestForm
from utils.callback_data import AnonymityCB, BuildingCB, CourseCB, RequestPreviewCB
from utils.formatting import request_preview_text

router = Router(name="user_request")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


@router.message(F.text == BTN_ASK)
async def start_request(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RequestForm.choosing_anonymity)
    await message.answer(
        "Хотите отправить обращение анонимно?", reply_markup=anonymity_kb()
    )


@router.callback_query(F.data == "reqcancel")
async def cancel_request(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отправка обращения отменена.")
    await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(RequestForm.choosing_anonymity, AnonymityCB.filter())
async def choose_anonymity(callback: CallbackQuery, callback_data: AnonymityCB, state: FSMContext) -> None:
    await state.update_data(is_anonymous=(callback_data.value == "yes"))
    await state.set_state(RequestForm.choosing_course)
    await callback.message.edit_text("Выберите ваш курс:", reply_markup=course_kb())
    await callback.answer()


@router.callback_query(RequestForm.choosing_course, CourseCB.filter())
async def choose_course(callback: CallbackQuery, callback_data: CourseCB, state: FSMContext) -> None:
    await state.update_data(course=callback_data.value)
    await state.set_state(RequestForm.choosing_building)
    await callback.message.edit_text("Выберите корпус обучения:", reply_markup=building_kb())
    await callback.answer()


@router.callback_query(RequestForm.choosing_building, BuildingCB.filter())
async def choose_building(callback: CallbackQuery, callback_data: BuildingCB, state: FSMContext) -> None:
    await state.update_data(building=callback_data.value)
    await state.set_state(RequestForm.entering_question)
    await callback.message.edit_text("✍️ Напишите ваш вопрос одним сообщением.")
    await callback.answer()


async def _show_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = request_preview_text(data["is_anonymous"], data["course"], data["building"], data["question"])
    await state.set_state(RequestForm.preview)
    await message.answer(text, reply_markup=request_preview_kb(), parse_mode="HTML")


@router.message(RequestForm.entering_question, F.text)
async def enter_question(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("Пожалуйста, отправьте текст вопроса одним сообщением.")
        return
    if len(text) > 4000:
        await message.answer("Текст вопроса слишком длинный. Пожалуйста, сократите его (до 4000 символов).")
        return
    await state.update_data(question=text)
    await _show_preview(message, state)


@router.message(RequestForm.entering_question)
async def enter_question_wrong_type(message: Message) -> None:
    await message.answer(
        "⚠️ Пока поддерживается только текст. Пожалуйста, опишите ваш вопрос словами."
    )


@router.callback_query(RequestForm.preview, RequestPreviewCB.filter(F.action == "cancel"))
async def preview_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await cancel_request(callback, state)


@router.callback_query(RequestForm.preview, RequestPreviewCB.filter(F.action == "edit"))
async def preview_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RequestForm.entering_question)
    await callback.message.edit_text("✍️ Напишите ваш вопрос одним сообщением ещё раз.")
    await callback.answer()


@router.callback_query(RequestForm.preview, RequestPreviewCB.filter(F.action == "send"))
async def preview_send(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    user = await crud.get_or_create_user(
        session, callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )
    request = await crud.create_request(
        session,
        user_id=user.id,
        is_anonymous=data["is_anonymous"],
        course=data["course"],
        building=data["building"],
        question_text=data["question"],
    )

    published = await publish_request_to_group(callback.bot, request, user)
    if published:
        chat_id, message_id = published
        await crud.set_request_group_message(session, request.id, chat_id, message_id)

    await state.clear()
    await callback.message.edit_text(
        f"📨 Ваше обращение #{request.id} принято.\n"
        "Мы передали его ответственным.\n"
        "Когда поступит ответ, мы сообщим вам."
    )
    await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()
