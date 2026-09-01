"""
Управление руководителями Студенческого совета (ТЗ, раздел 11).

Поддерживается: добавление, полное редактирование каждого поля (включая
замену/удаление фото), включение/выключение видимости для студентов,
удаление записи целиком.
"""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import (
    form_control_kb,
    form_preview_kb,
    leader_detail_admin_kb,
    leader_edit_menu_kb,
    leaders_list_admin_kb,
)
from states.states import CouncilLeaderEditForm, CouncilLeaderForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, FormControlCB, LeaderAdminCB
from utils.formatting import escape_html, leader_position_detail_text

router = Router(name="admin_leaders")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

FIELD_LABELS = {
    "full_name": "ФИО",
    "position": "должность",
    "telegram_username": "Telegram username",
}
FIELD_MAX_LENGTHS = {
    "full_name": 200,
    "position": 250,
    "telegram_username": 64,
}


def _detail_text(leader) -> str:
    return (
        f"👤 <b>{escape_html(leader.full_name)}</b>\n"
        f"{escape_html(leader_position_detail_text(leader.position))}\n"
        f"Telegram: @{escape_html(leader.telegram_username or '—')}\n"
        f"Фото: {'есть' if leader.photo_file_id else 'нет'}\n"
        f"Видимость: {'👁 показывается студентам' if leader.is_active else '🚫 скрыто от студентов'}"
    )


async def _render_detail(target_message: Message, leader, edit: bool = True) -> None:
    text = _detail_text(leader)
    kb = leader_detail_admin_kb(leader)
    if leader.photo_file_id:
        await target_message.answer_photo(photo=leader.photo_file_id, caption=text, reply_markup=kb, parse_mode="HTML")
    elif edit:
        await target_message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target_message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminMenuCB.filter(F.target == "leaders"))
async def cb_list(callback: CallbackQuery, session: AsyncSession) -> None:
    leaders = await crud.list_council_leaders(session, only_active=False)
    text = "👥 <b>Руководители Студсовета</b>\n\n" + ("Список пуст." if not leaders else "Выберите запись:")
    await callback.message.edit_text(text, reply_markup=leaders_list_admin_kb(leaders), parse_mode="HTML")
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "list"))
async def cb_list_back(callback: CallbackQuery, session: AsyncSession) -> None:
    leaders = await crud.list_council_leaders(session, only_active=False)
    text = "👥 <b>Руководители Студсовета</b>\n\n" + ("Список пуст." if not leaders else "Выберите запись:")
    try:
        await callback.message.edit_text(text, reply_markup=leaders_list_admin_kb(leaders), parse_mode="HTML")
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=leaders_list_admin_kb(leaders), parse_mode="HTML")
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "admview"))
async def cb_view(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    leader = await crud.get_council_leader(session, callback_data.leader_id)
    if not leader:
        await callback.answer("Не найдено.", show_alert=True)
        return
    if leader.photo_file_id:
        await callback.message.delete()
        await _render_detail(callback.message, leader, edit=False)
    else:
        await callback.message.edit_text(_detail_text(leader), reply_markup=leader_detail_admin_kb(leader), parse_mode="HTML")
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "delete"))
async def cb_delete(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    ok = await crud.delete_council_leader(session, callback_data.leader_id)
    leaders = await crud.list_council_leaders(session, only_active=False)
    text = "🗑 Удалено." if ok else "Не удалось удалить."
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=leaders_list_admin_kb(leaders))
    else:
        await callback.message.edit_text(text, reply_markup=leaders_list_admin_kb(leaders))
    await callback.answer()


# ---------------------- Видимость (показать/скрыть) ------------------------

@router.callback_query(LeaderAdminCB.filter(F.action == "toggle_active"))
async def cb_toggle_active(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    leader = await crud.get_council_leader(session, callback_data.leader_id)
    if not leader:
        await callback.answer("Не найдено.", show_alert=True)
        return
    leader = await crud.set_council_leader_active(session, leader.id, not leader.is_active)
    if callback.message.photo:
        await callback.message.edit_caption(caption=_detail_text(leader), reply_markup=leader_detail_admin_kb(leader), parse_mode="HTML")
    else:
        await callback.message.edit_text(_detail_text(leader), reply_markup=leader_detail_admin_kb(leader), parse_mode="HTML")
    await callback.answer("Видимость обновлена")


# ---------------------- Редактирование существующей записи -----------------

@router.callback_query(LeaderAdminCB.filter(F.action == "edit_menu"))
async def cb_edit_menu(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    leader = await crud.get_council_leader(session, callback_data.leader_id)
    if not leader:
        await callback.answer("Не найдено.", show_alert=True)
        return
    text = f"✏️ Что изменить у «{escape_html(leader.full_name)}»?"
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=leader_edit_menu_kb(leader),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=leader_edit_menu_kb(leader),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "edit_field"))
async def cb_edit_field_start(callback: CallbackQuery, callback_data: LeaderAdminCB, state: FSMContext) -> None:
    await state.set_state(CouncilLeaderEditForm.entering_value)
    await state.update_data(leader_id=callback_data.leader_id, field=callback_data.field)
    if callback_data.field == "photo":
        prompt = "Отправьте новое фото:"
    else:
        label = FIELD_LABELS.get(callback_data.field, callback_data.field)
        prompt = f"Введите новое значение поля «{label}»:"
        if callback_data.field == "telegram_username":
            prompt += " (без «@»)"
    await callback.message.answer(prompt, reply_markup=form_control_kb())
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "delete_photo"))
async def cb_delete_photo(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    leader = await crud.update_council_leader(session, callback_data.leader_id, photo_file_id=None)
    if not leader:
        await callback.answer("Не найдено.", show_alert=True)
        return
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(_detail_text(leader), reply_markup=leader_detail_admin_kb(leader), parse_mode="HTML")
    else:
        await callback.message.edit_text(_detail_text(leader), reply_markup=leader_detail_admin_kb(leader), parse_mode="HTML")
    await callback.answer("Фото удалено")


@router.message(CouncilLeaderEditForm.entering_value, F.text)
async def edit_field_receive_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["field"] == "photo":
        await message.answer("⚠️ Пожалуйста, отправьте фото (не текст).")
        return
    value = message.text.strip()
    if data["field"] == "telegram_username":
        value = value.lstrip("@")
    if not value:
        await message.answer("Значение не может быть пустым.")
        return
    max_length = FIELD_MAX_LENGTHS[data["field"]]
    if len(value) > max_length:
        await message.answer(f"⚠️ Максимум — {max_length} символов.")
        return
    await state.update_data(new_value=value)
    await state.set_state(CouncilLeaderEditForm.preview)
    label = FIELD_LABELS.get(data["field"], data["field"])
    await message.answer(
        f"Предпросмотр — {label}:\n\n{escape_html(value)}",
        reply_markup=form_preview_kb(),
        parse_mode="HTML",
    )


@router.message(CouncilLeaderEditForm.entering_value, F.photo)
async def edit_field_receive_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["field"] != "photo":
        await message.answer("⚠️ Ожидался текст, а не фото.")
        return
    file_id = message.photo[-1].file_id
    await state.update_data(new_value=file_id)
    await state.set_state(CouncilLeaderEditForm.preview)
    await message.answer_photo(photo=file_id, caption="Предпросмотр нового фото:", reply_markup=form_preview_kb())


@router.callback_query(StateFilter(CouncilLeaderForm, CouncilLeaderEditForm), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("CouncilLeaderForm"):
        await state.clear()
        leaders = await crud.list_council_leaders(session, only_active=False)
        await callback.message.edit_text("❌ Добавление отменено.", reply_markup=leaders_list_admin_kb(leaders))
        await callback.answer()
    elif current_state.startswith("CouncilLeaderEditForm"):
        data = await state.get_data()
        await state.clear()
        leader = await crud.get_council_leader(session, data.get("leader_id"))
        await callback.answer("Отменено")
        if leader:
            await _render_detail(callback.message, leader, edit=False)


@router.callback_query(CouncilLeaderEditForm.preview, FormControlCB.filter(F.action == "save"))
async def edit_field_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = "photo_file_id" if data["field"] == "photo" else data["field"]
    leader = await crud.update_council_leader(session, data["leader_id"], **{field: data["new_value"]})
    await state.clear()
    if not leader:
        await callback.message.answer("⚠️ Запись не найдена.")
        await callback.answer()
        return
    await callback.answer("Сохранено")
    await _render_detail(callback.message, leader, edit=False)


# ---------------------------- Добавление ---------------------------------

@router.callback_query(LeaderAdminCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CouncilLeaderForm.entering_full_name)
    await callback.message.edit_text("Введите ФИО руководителя:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(CouncilLeaderForm.entering_full_name, F.text)
async def add_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if not full_name or len(full_name) > FIELD_MAX_LENGTHS["full_name"]:
        await message.answer("⚠️ Укажите ФИО длиной до 200 символов.")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(CouncilLeaderForm.entering_position)
    await message.answer("Введите должность:", reply_markup=form_control_kb())


@router.message(CouncilLeaderForm.entering_position, F.text)
async def add_position(message: Message, state: FSMContext) -> None:
    position = message.text.strip()
    if not position or len(position) > FIELD_MAX_LENGTHS["position"]:
        await message.answer("⚠️ Укажите должность длиной до 250 символов.")
        return
    await state.update_data(position=position)
    await state.set_state(CouncilLeaderForm.entering_username)
    await message.answer(
        "Введите Telegram username без «@» или «-», если пропустить:", reply_markup=form_control_kb()
    )


@router.message(CouncilLeaderForm.entering_username, F.text)
async def add_username(message: Message, state: FSMContext) -> None:
    username = None if message.text.strip() == "-" else message.text.strip().lstrip("@")
    if username and (len(username) > FIELD_MAX_LENGTHS["telegram_username"] or " " in username):
        await message.answer("⚠️ Введите корректный username без «@» или «-».")
        return
    await state.update_data(telegram_username=username)
    await state.set_state(CouncilLeaderForm.entering_photo)
    await message.answer("Отправьте фото или «-», если без фото:", reply_markup=form_control_kb())


@router.message(CouncilLeaderForm.entering_photo, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await _show_preview(message, state)


@router.message(CouncilLeaderForm.entering_photo, F.text == "-")
async def add_photo_skip(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=None)
    await _show_preview(message, state)


@router.message(CouncilLeaderForm.entering_photo)
async def add_photo_wrong(message: Message) -> None:
    await message.answer("⚠️ Пришлите фото или «-».")


async def _show_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(CouncilLeaderForm.preview)
    text = (
        "Предпросмотр:\n\n"
        f"👤 {escape_html(data['full_name'])}\n{escape_html(data['position'])}\n"
        f"Telegram: @{escape_html(data.get('telegram_username') or '—')}\n"
        f"Фото: {'да' if data.get('photo_file_id') else 'нет'}"
    )
    await message.answer(text, reply_markup=form_preview_kb(), parse_mode="HTML")


@router.callback_query(CouncilLeaderForm.preview, FormControlCB.filter(F.action == "save"))
async def add_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await crud.add_council_leader(
        session,
        full_name=data["full_name"],
        position=data["position"],
        telegram_username=data.get("telegram_username"),
        photo_file_id=data.get("photo_file_id"),
    )
    await state.clear()
    leaders = await crud.list_council_leaders(session, only_active=False)
    await callback.message.edit_text("✅ Руководитель добавлен.", reply_markup=leaders_list_admin_kb(leaders))
    await callback.answer()
