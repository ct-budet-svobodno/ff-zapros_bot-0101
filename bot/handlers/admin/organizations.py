"""
Управление студенческими организациями (НСО, клубы, комитеты, творческие
коллективы) — ТЗ, раздел 9. Категория задаётся свободным текстом при
добавлении, поэтому список категорий в боте всегда актуален и не требует
изменения кода при появлении новых организаций.

Поддерживается полное редактирование (категория/название/описание/ссылка),
включение/выключение видимости для студентов, удаление.
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
    org_detail_admin_kb,
    org_edit_menu_kb,
    orgs_categories_admin_kb,
    orgs_list_admin_kb,
)
from states.states import OrganizationEditForm, OrganizationForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, FormControlCB, OrgAdminCB

router = Router(name="admin_organizations")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

FIELD_LABELS = {
    "category": "категория",
    "name": "название",
    "description": "описание",
    "link": "ссылка",
}


def _detail_text(org) -> str:
    text = f"🤝 <b>{org.name}</b>\n\nКатегория: {org.category}\n\n{org.description or '—'}"
    if org.link:
        text += f"\n\n🔗 {org.link}"
    text += f"\n\nВидимость: {'👁 показывается студентам' if org.is_active else '🚫 скрыто от студентов'}"
    return text


@router.callback_query(AdminMenuCB.filter(F.target == "content_orgs"))
async def cb_categories(callback: CallbackQuery, session: AsyncSession) -> None:
    categories = await crud.list_org_categories(session)
    text = "🤝 <b>Студенческие организации</b>\n\n" + (
        "Категорий пока нет. Добавьте первую организацию." if not categories else "Выберите категорию:"
    )
    await callback.message.edit_text(text, reply_markup=orgs_categories_admin_kb(categories), parse_mode="HTML")
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "choose_cat"))
async def cb_category_items(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    items = await crud.list_organizations(session, category=callback_data.category, only_active=False)
    text = f"🤝 <b>{callback_data.category}</b>\n\n" + ("Пусто." if not items else "Выберите организацию:")
    await callback.message.edit_text(
        text, reply_markup=orgs_list_admin_kb(items, callback_data.category), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "view"))
async def cb_view(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    org = await crud.get_organization(session, callback_data.org_id)
    if not org:
        await callback.answer("Не найдено.", show_alert=True)
        return
    await callback.message.edit_text(_detail_text(org), reply_markup=org_detail_admin_kb(org), parse_mode="HTML")
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "delete"))
async def cb_delete(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    ok = await crud.delete_organization(session, callback_data.org_id)
    items = await crud.list_organizations(session, category=callback_data.category, only_active=False)
    await callback.message.edit_text(
        "🗑 Организация удалена." if ok else "Не удалось удалить.",
        reply_markup=orgs_list_admin_kb(items, callback_data.category),
    )
    await callback.answer()


# ---------------------- Видимость (показать/скрыть) ------------------------

@router.callback_query(OrgAdminCB.filter(F.action == "toggle_active"))
async def cb_toggle_active(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    org = await crud.get_organization(session, callback_data.org_id)
    if not org:
        await callback.answer("Не найдено.", show_alert=True)
        return
    org = await crud.set_organization_active(session, org.id, not org.is_active)
    await callback.message.edit_text(_detail_text(org), reply_markup=org_detail_admin_kb(org), parse_mode="HTML")
    await callback.answer("Видимость обновлена")


# ---------------------- Редактирование существующей записи -----------------

@router.callback_query(OrgAdminCB.filter(F.action == "edit_menu"))
async def cb_edit_menu(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    org = await crud.get_organization(session, callback_data.org_id)
    if not org:
        await callback.answer("Не найдено.", show_alert=True)
        return
    await callback.message.edit_text(f"✏️ Что изменить у «{org.name}»?", reply_markup=org_edit_menu_kb(org))
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "edit_field"))
async def cb_edit_field_start(callback: CallbackQuery, callback_data: OrgAdminCB, state: FSMContext) -> None:
    await state.set_state(OrganizationEditForm.entering_value)
    await state.update_data(org_id=callback_data.org_id, field=callback_data.field, nav_category=callback_data.category)
    label = FIELD_LABELS.get(callback_data.field, callback_data.field)
    await callback.message.edit_text(f"Введите новое значение поля «{label}»:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(OrganizationEditForm.entering_value, F.text)
async def edit_field_receive_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    value = message.text.strip()
    if not value:
        await message.answer("Значение не может быть пустым.")
        return
    if data["field"] == "link" and value == "-":
        value = ""
    await state.update_data(new_value=value)
    await state.set_state(OrganizationEditForm.preview)
    label = FIELD_LABELS.get(data["field"], data["field"])
    await message.answer(f"Предпросмотр — {label}:\n\n{value or '—'}", reply_markup=form_preview_kb())


@router.callback_query(StateFilter(OrganizationForm, OrganizationEditForm), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("OrganizationForm"):
        await state.clear()
        categories = await crud.list_org_categories(session)
        await callback.message.edit_text("❌ Добавление отменено.", reply_markup=orgs_categories_admin_kb(categories))
        await callback.answer()
    elif current_state.startswith("OrganizationEditForm"):
        data = await state.get_data()
        await state.clear()
        org = await crud.get_organization(session, data.get("org_id"))
        await callback.answer("Отменено")
        if org:
            await callback.message.answer(_detail_text(org), reply_markup=org_detail_admin_kb(org), parse_mode="HTML")


@router.callback_query(OrganizationEditForm.preview, FormControlCB.filter(F.action == "save"))
async def edit_field_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    value = data["new_value"] if data["new_value"] else None
    org = await crud.update_organization(session, data["org_id"], **{data["field"]: value})
    await state.clear()
    if not org:
        await callback.message.answer("⚠️ Организация не найдена.")
        await callback.answer()
        return
    await callback.answer("Сохранено")
    await callback.message.answer(_detail_text(org), reply_markup=org_detail_admin_kb(org), parse_mode="HTML")


# ---------------------------- Добавление ---------------------------------

@router.callback_query(OrgAdminCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, callback_data: OrgAdminCB, state: FSMContext) -> None:
    if callback_data.category:
        await state.update_data(category=callback_data.category)
        await state.set_state(OrganizationForm.entering_name)
        await callback.message.edit_text("Введите название организации:", reply_markup=form_control_kb())
    else:
        await state.set_state(OrganizationForm.choosing_category)
        await callback.message.edit_text(
            "Введите название категории (например: «Комитеты», «Клубы», «Творческие коллективы»):",
            reply_markup=form_control_kb(),
        )
    await callback.answer()


@router.message(OrganizationForm.choosing_category, F.text)
async def add_category(message: Message, state: FSMContext) -> None:
    await state.update_data(category=message.text.strip())
    await state.set_state(OrganizationForm.entering_name)
    await message.answer("Введите название организации:", reply_markup=form_control_kb())


@router.message(OrganizationForm.entering_name, F.text)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(OrganizationForm.entering_description)
    await message.answer(
        "Введите краткое описание или «-», если пропустить:", reply_markup=form_control_kb()
    )


@router.message(OrganizationForm.entering_description, F.text)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(OrganizationForm.entering_link)
    await message.answer(
        "Введите ссылку (Telegram/VK и т.п.) или «-», если пропустить:", reply_markup=form_control_kb()
    )


@router.message(OrganizationForm.entering_link, F.text)
async def add_link(message: Message, state: FSMContext) -> None:
    link = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(link=link)
    await state.set_state(OrganizationForm.preview)
    data = await state.get_data()
    text = (
        "Предпросмотр:\n\n"
        f"Категория: {data['category']}\n"
        f"Название: {data['name']}\n"
        f"Описание: {data.get('description') or '—'}\n"
        f"Ссылка: {data.get('link') or '—'}"
    )
    await message.answer(text, reply_markup=form_preview_kb())


@router.callback_query(OrganizationForm.preview, FormControlCB.filter(F.action == "save"))
async def add_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await crud.add_organization(
        session,
        category=data["category"],
        name=data["name"],
        description=data.get("description"),
        link=data.get("link"),
    )
    await state.clear()
    items = await crud.list_organizations(session, category=data["category"], only_active=False)
    await callback.message.edit_text(
        "✅ Организация добавлена.", reply_markup=orgs_list_admin_kb(items, data["category"])
    )
    await callback.answer()
