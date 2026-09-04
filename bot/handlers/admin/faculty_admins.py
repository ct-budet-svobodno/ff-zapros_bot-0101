"""
Управление списком представителей администрации факультета
(ФИО, должность, фото, контакты) — ТЗ, раздел 8.

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
    fadmin_detail_kb,
    fadmin_edit_menu_kb,
    fadmins_list_kb,
    form_control_kb,
    form_preview_kb,
)
from states.states import FacultyAdminEditForm, FacultyAdminForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, FacultyAdminCB, FormControlCB
from utils.formatting import escape_html
from utils.navigation import show_text_screen

router = Router(name="admin_faculty_admins")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

FIELD_LABELS = {
    "full_name": "ФИО",
    "position": "должность",
    "contact_info": "контакты",
}
FIELD_MAX_LENGTHS = {
    "full_name": 200,
    "position": 250,
    "contact_info": 500,
}


def _detail_text(person) -> str:
    return (
        f"👤 <b>{escape_html(person.full_name)}</b>\n"
        f"{escape_html(person.position)}\n\n"
        f"Контакты: {escape_html(person.contact_info or '—')}\n"
        f"Фото: {'есть' if person.photo_file_id else 'нет'}\n"
        f"Видимость: {'👁 показывается студентам' if person.is_active else '🚫 скрыто от студентов'}"
    )


async def _render_detail(target_message: Message, person, edit: bool = True) -> None:
    text = _detail_text(person)
    kb = fadmin_detail_kb(person)
    if person.photo_file_id:
        await target_message.answer_photo(photo=person.photo_file_id, caption=text, reply_markup=kb, parse_mode="HTML")
    elif edit:
        await target_message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target_message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminMenuCB.filter(F.target == "content_fadmins"))
async def cb_list(callback: CallbackQuery, session: AsyncSession) -> None:
    people = await crud.list_faculty_admins(session, only_active=False)
    text = "👥 <b>Администрация факультета</b>\n\n" + (
        "Список пуст. Добавьте первого представителя." if not people else "Выберите запись:"
    )
    await show_text_screen(callback.message, text, reply_markup=fadmins_list_kb(people), parse_mode="HTML")
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "list"))
async def cb_list_back(callback: CallbackQuery, session: AsyncSession) -> None:
    people = await crud.list_faculty_admins(session, only_active=False)
    text = "👥 <b>Администрация факультета</b>\n\n" + (
        "Список пуст. Добавьте первого представителя." if not people else "Выберите запись:"
    )
    await show_text_screen(callback.message, text, reply_markup=fadmins_list_kb(people), parse_mode="HTML")
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "admview"))
async def cb_view(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    person = await crud.get_faculty_admin(session, callback_data.person_id)
    if not person:
        await callback.answer("Не найдено.", show_alert=True)
        return
    if person.photo_file_id:
        await callback.message.delete()
        await _render_detail(callback.message, person, edit=False)
    else:
        await show_text_screen(callback.message, _detail_text(person), reply_markup=fadmin_detail_kb(person), parse_mode="HTML")
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "delete"))
async def cb_delete(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    ok = await crud.delete_faculty_admin(session, callback_data.person_id)
    people = await crud.list_faculty_admins(session, only_active=False)
    text = "🗑 Запись удалена." if ok else "Не удалось удалить."
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=fadmins_list_kb(people))
    else:
        await callback.message.edit_text(text, reply_markup=fadmins_list_kb(people))
    await callback.answer()


# ---------------------- Видимость (показать/скрыть) ------------------------

@router.callback_query(FacultyAdminCB.filter(F.action == "toggle_active"))
async def cb_toggle_active(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    person = await crud.get_faculty_admin(session, callback_data.person_id)
    if not person:
        await callback.answer("Не найдено.", show_alert=True)
        return
    person = await crud.set_faculty_admin_active(session, person.id, not person.is_active)
    if callback.message.photo:
        await callback.message.edit_caption(caption=_detail_text(person), reply_markup=fadmin_detail_kb(person), parse_mode="HTML")
    else:
        await callback.message.edit_text(_detail_text(person), reply_markup=fadmin_detail_kb(person), parse_mode="HTML")
    await callback.answer("Видимость обновлена")


# ---------------------- Редактирование существующей записи -----------------

@router.callback_query(FacultyAdminCB.filter(F.action == "edit_menu"))
async def cb_edit_menu(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    person = await crud.get_faculty_admin(session, callback_data.person_id)
    if not person:
        await callback.answer("Не найдено.", show_alert=True)
        return
    text = f"✏️ Что изменить у «{escape_html(person.full_name)}»?"
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=fadmin_edit_menu_kb(person),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=fadmin_edit_menu_kb(person),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "edit_field"))
async def cb_edit_field_start(callback: CallbackQuery, callback_data: FacultyAdminCB, state: FSMContext) -> None:
    await state.set_state(FacultyAdminEditForm.entering_value)
    await state.update_data(person_id=callback_data.person_id, field=callback_data.field)
    if callback_data.field == "photo":
        prompt = "Отправьте новое фото:"
    else:
        label = FIELD_LABELS.get(callback_data.field, callback_data.field)
        prompt = f"Введите новое значение поля «{label}»:"
    await callback.message.answer(prompt, reply_markup=form_control_kb())
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "delete_photo"))
async def cb_delete_photo(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    person = await crud.update_faculty_admin(session, callback_data.person_id, photo_file_id=None)
    if not person:
        await callback.answer("Не найдено.", show_alert=True)
        return
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(_detail_text(person), reply_markup=fadmin_detail_kb(person), parse_mode="HTML")
    else:
        await callback.message.edit_text(_detail_text(person), reply_markup=fadmin_detail_kb(person), parse_mode="HTML")
    await callback.answer("Фото удалено")


@router.message(FacultyAdminEditForm.entering_value, F.text)
async def edit_field_receive_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["field"] == "photo":
        await message.answer("⚠️ Пожалуйста, отправьте фото (не текст).")
        return
    value = message.text.strip()
    if not value:
        await message.answer("Значение не может быть пустым.")
        return
    max_length = FIELD_MAX_LENGTHS[data["field"]]
    if len(value) > max_length:
        await message.answer(f"⚠️ Максимум — {max_length} символов.")
        return
    await state.update_data(new_value=value)
    await state.set_state(FacultyAdminEditForm.preview)
    label = FIELD_LABELS.get(data["field"], data["field"])
    await message.answer(
        f"Предпросмотр — {label}:\n\n{escape_html(value)}",
        reply_markup=form_preview_kb(),
        parse_mode="HTML",
    )


@router.message(FacultyAdminEditForm.entering_value, F.photo)
async def edit_field_receive_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["field"] != "photo":
        await message.answer("⚠️ Ожидался текст, а не фото. Пожалуйста, отправьте текстовое значение.")
        return
    file_id = message.photo[-1].file_id
    await state.update_data(new_value=file_id)
    await state.set_state(FacultyAdminEditForm.preview)
    await message.answer_photo(photo=file_id, caption="Предпросмотр нового фото:", reply_markup=form_preview_kb())


@router.callback_query(StateFilter(FacultyAdminForm, FacultyAdminEditForm), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("FacultyAdminForm"):
        await state.clear()
        people = await crud.list_faculty_admins(session, only_active=False)
        await callback.message.edit_text("❌ Добавление отменено.", reply_markup=fadmins_list_kb(people))
        await callback.answer()
    elif current_state.startswith("FacultyAdminEditForm"):
        data = await state.get_data()
        await state.clear()
        person = await crud.get_faculty_admin(session, data.get("person_id"))
        await callback.answer("Отменено")
        if person:
            await _render_detail(callback.message, person, edit=False)


@router.callback_query(FacultyAdminEditForm.preview, FormControlCB.filter(F.action == "save"))
async def edit_field_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = "photo_file_id" if data["field"] == "photo" else data["field"]
    person = await crud.update_faculty_admin(session, data["person_id"], **{field: data["new_value"]})
    await state.clear()
    if not person:
        await callback.message.answer("⚠️ Запись не найдена.")
        await callback.answer()
        return
    await callback.answer("Сохранено")
    await _render_detail(callback.message, person, edit=False)


# ---------------------------- Добавление ---------------------------------

@router.callback_query(FacultyAdminCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FacultyAdminForm.entering_full_name)
    await callback.message.edit_text("Введите ФИО представителя администрации:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(FacultyAdminForm.entering_full_name, F.text)
async def add_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if not full_name or len(full_name) > FIELD_MAX_LENGTHS["full_name"]:
        await message.answer("⚠️ Укажите ФИО длиной до 200 символов.")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(FacultyAdminForm.entering_position)
    await message.answer("Введите должность:", reply_markup=form_control_kb())


@router.message(FacultyAdminForm.entering_position, F.text)
async def add_position(message: Message, state: FSMContext) -> None:
    position = message.text.strip()
    if not position or len(position) > FIELD_MAX_LENGTHS["position"]:
        await message.answer("⚠️ Укажите должность длиной до 250 символов.")
        return
    await state.update_data(position=position)
    await state.set_state(FacultyAdminForm.entering_contact)
    await message.answer(
        "Введите контактную информацию (email/телефон/ссылку) или отправьте «-», если пропустить:",
        reply_markup=form_control_kb(),
    )


@router.message(FacultyAdminForm.entering_contact, F.text)
async def add_contact(message: Message, state: FSMContext) -> None:
    contact = None if message.text.strip() == "-" else message.text.strip()
    if contact and len(contact) > FIELD_MAX_LENGTHS["contact_info"]:
        await message.answer("⚠️ Контактная информация не должна превышать 500 символов.")
        return
    await state.update_data(contact_info=contact)
    await state.set_state(FacultyAdminForm.entering_photo)
    await message.answer(
        "Отправьте фото представителя администрации или «-», если без фото:",
        reply_markup=form_control_kb(),
    )


@router.message(FacultyAdminForm.entering_photo, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)
    await _show_add_preview(message, state)


@router.message(FacultyAdminForm.entering_photo, F.text == "-")
async def add_photo_skip(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=None)
    await _show_add_preview(message, state)


@router.message(FacultyAdminForm.entering_photo)
async def add_photo_wrong(message: Message) -> None:
    await message.answer("⚠️ Пришлите фото или «-», если фото не нужно.")


async def _show_add_preview(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(FacultyAdminForm.preview)
    text = (
        "Предпросмотр:\n\n"
        f"👤 {escape_html(data['full_name'])}\n"
        f"{escape_html(data['position'])}\n"
        f"Контакты: {escape_html(data.get('contact_info') or '—')}\n"
        f"Фото: {'да' if data.get('photo_file_id') else 'нет'}"
    )
    await message.answer(text, reply_markup=form_preview_kb(), parse_mode="HTML")


@router.callback_query(FacultyAdminForm.preview, FormControlCB.filter(F.action == "save"))
async def add_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await crud.add_faculty_admin(
        session,
        full_name=data["full_name"],
        position=data["position"],
        contact_info=data.get("contact_info"),
        photo_file_id=data.get("photo_file_id"),
    )
    await state.clear()
    people = await crud.list_faculty_admins(session, only_active=False)
    await callback.message.edit_text("✅ Представитель администрации добавлен.", reply_markup=fadmins_list_kb(people))
    await callback.answer()
