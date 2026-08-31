"""Управление дайджестом мероприятий (ТЗ, раздел 12): создать / изменить / удалить."""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import digest_detail_admin_kb, digests_list_admin_kb, form_control_kb, form_preview_kb
from states.states import DigestEdit, DigestForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, DigestAdminCB, FormControlCB
from utils.formatting import escape_html

router = Router(name="admin_digests")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MAX_DIGEST_MONTH_LENGTH = 32
MAX_DIGEST_TITLE_LENGTH = 200
MAX_DIGEST_TEXT_LENGTH = 3500


@router.callback_query(AdminMenuCB.filter(F.target == "digests"))
async def cb_list(callback: CallbackQuery, session: AsyncSession) -> None:
    digests = await crud.list_digests(session, only_active=False)
    text = "📅 <b>Дайджест мероприятий</b>\n\n" + ("Пока нет ни одного дайджеста." if not digests else "Выберите:")
    await callback.message.edit_text(text, reply_markup=digests_list_admin_kb(digests), parse_mode="HTML")
    await callback.answer()


@router.callback_query(DigestAdminCB.filter(F.action == "list"))
async def cb_list_back(callback: CallbackQuery, session: AsyncSession) -> None:
    await cb_list(callback, session)


@router.callback_query(DigestAdminCB.filter(F.action == "view"))
async def cb_view(callback: CallbackQuery, callback_data: DigestAdminCB, session: AsyncSession) -> None:
    digest = await crud.get_digest(session, callback_data.digest_id)
    if not digest:
        await callback.answer("Не найдено.", show_alert=True)
        return
    text = (
        f"📅 <b>{escape_html(digest.title)}</b> "
        f"({escape_html(digest.month_label)})\n\n{escape_html(digest.text)}"
    )
    await callback.message.edit_text(text, reply_markup=digest_detail_admin_kb(digest.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(DigestAdminCB.filter(F.action == "delete"))
async def cb_delete(callback: CallbackQuery, callback_data: DigestAdminCB, session: AsyncSession) -> None:
    ok = await crud.delete_digest(session, callback_data.digest_id)
    digests = await crud.list_digests(session, only_active=False)
    await callback.message.edit_text(
        "🗑 Дайджест удалён." if ok else "Не удалось удалить.", reply_markup=digests_list_admin_kb(digests)
    )
    await callback.answer()


# ---------------------------- Создание ------------------------------------

@router.callback_query(DigestAdminCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DigestForm.entering_month)
    await callback.message.edit_text(
        "Введите месяц дайджеста (например: «Август 2026»):", reply_markup=form_control_kb()
    )
    await callback.answer()


@router.callback_query(StateFilter(DigestForm, DigestEdit), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("DigestForm"):
        await state.clear()
        digests = await crud.list_digests(session, only_active=False)
        await callback.message.edit_text("❌ Создание отменено.", reply_markup=digests_list_admin_kb(digests))
        await callback.answer()
    elif current_state.startswith("DigestEdit"):
        data = await state.get_data()
        await state.clear()
        digest = await crud.get_digest(session, data.get("digest_id"))
        if digest:
            await callback.message.edit_text(
                f"📅 <b>{escape_html(digest.title)}</b> "
                f"({escape_html(digest.month_label)})\n\n{escape_html(digest.text)}",
                reply_markup=digest_detail_admin_kb(digest.id),
                parse_mode="HTML",
            )
        await callback.answer("Отменено")


@router.message(DigestForm.entering_month, F.text)
async def add_month(message: Message, state: FSMContext) -> None:
    month = message.text.strip()
    if not month or len(month) > MAX_DIGEST_MONTH_LENGTH:
        await message.answer("⚠️ Укажите месяц длиной до 32 символов.")
        return
    await state.update_data(month_label=month)
    await state.set_state(DigestForm.entering_title)
    await message.answer("Введите заголовок дайджеста:", reply_markup=form_control_kb())


@router.message(DigestForm.entering_title, F.text)
async def add_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title or len(title) > MAX_DIGEST_TITLE_LENGTH:
        await message.answer("⚠️ Укажите заголовок длиной до 200 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(DigestForm.entering_text)
    await message.answer("Введите текст дайджеста:", reply_markup=form_control_kb())


@router.message(DigestForm.entering_text, F.text)
async def add_text(message: Message, state: FSMContext) -> None:
    digest_text = message.text.strip()
    if not digest_text:
        await message.answer("⚠️ Текст дайджеста не может быть пустым.")
        return
    if len(digest_text) > MAX_DIGEST_TEXT_LENGTH:
        await message.answer(
            f"⚠️ Текст слишком длинный. Максимум — {MAX_DIGEST_TEXT_LENGTH} символов."
        )
        return
    await state.update_data(text=digest_text)
    await state.set_state(DigestForm.preview)
    data = await state.get_data()
    preview = (
        f"Предпросмотр:\n\n📅 {escape_html(data['title'])} "
        f"({escape_html(data['month_label'])})\n\n{escape_html(data['text'])}"
    )
    await message.answer(preview, reply_markup=form_preview_kb(), parse_mode="HTML")


@router.callback_query(DigestForm.preview, FormControlCB.filter(F.action == "save"))
async def add_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await crud.add_digest(session, month_label=data["month_label"], title=data["title"], text=data["text"])
    await state.clear()
    digests = await crud.list_digests(session, only_active=False)
    await callback.message.edit_text("✅ Дайджест создан.", reply_markup=digests_list_admin_kb(digests))
    await callback.answer()


# ---------------------------- Изменение текста -----------------------------

@router.callback_query(DigestAdminCB.filter(F.action == "edit"))
async def cb_edit_start(callback: CallbackQuery, callback_data: DigestAdminCB, state: FSMContext) -> None:
    await state.set_state(DigestEdit.entering_text)
    await state.update_data(digest_id=callback_data.digest_id)
    await callback.message.edit_text("Отправьте новый текст дайджеста:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(DigestEdit.entering_text, F.text)
async def edit_text_receive(message: Message, state: FSMContext) -> None:
    digest_text = message.text.strip()
    if not digest_text:
        await message.answer("⚠️ Текст дайджеста не может быть пустым.")
        return
    if len(digest_text) > MAX_DIGEST_TEXT_LENGTH:
        await message.answer(
            f"⚠️ Текст слишком длинный. Максимум — {MAX_DIGEST_TEXT_LENGTH} символов."
        )
        return
    await state.update_data(new_text=digest_text)
    await state.set_state(DigestEdit.preview)
    await message.answer(
        f"Предпросмотр:\n\n{escape_html(digest_text)}",
        reply_markup=form_preview_kb(),
        parse_mode="HTML",
    )


@router.callback_query(DigestEdit.preview, FormControlCB.filter(F.action == "save"))
async def edit_text_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    digest = await crud.update_digest_text(session, data["digest_id"], data["new_text"])
    await state.clear()
    if digest:
        await callback.message.edit_text(
            f"✅ Дайджест обновлён.\n\n📅 {escape_html(digest.title)} "
            f"({escape_html(digest.month_label)})\n\n{escape_html(digest.text)}",
            reply_markup=digest_detail_admin_kb(digest.id),
            parse_mode="HTML",
        )
    await callback.answer()
