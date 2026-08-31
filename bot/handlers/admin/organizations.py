"""
Управление студенческими организациями (НСО, клубы, комитеты, творческие
коллективы) — ТЗ, раздел 9. Категория задаётся свободным текстом при
добавлении, поэтому список категорий в боте всегда актуален и не требует
изменения кода при появлении новых организаций.

Поддерживается полное редактирование (категория/название/описание/ссылка),
включение/выключение видимости для студентов, удаление.
"""
from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import (
    form_control_kb,
    form_preview_kb,
    org_clear_text_confirm_kb,
    org_detail_admin_kb,
    org_edit_menu_kb,
    orgs_categories_admin_kb,
    orgs_list_admin_kb,
)
from states.states import OrganizationEditForm, OrganizationForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, FormControlCB, OrgAdminCB
from utils.formatting import escape_html

router = Router(name="admin_organizations")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

FIELD_LABELS = {
    "category": "категория",
    "name": "название",
    "description": "описание",
    "link": "ссылка",
}
MAX_ORGANIZATION_TEXT_LENGTH = 1500
FIELD_MAX_LENGTHS = {
    "category": 64,
    "name": 255,
    "description": MAX_ORGANIZATION_TEXT_LENGTH,
    "link": 255,
}


def _normalize_link(value: str) -> str | None:
    if value == "-":
        return None
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _detail_text(org) -> str:
    text = (
        f"🤝 <b>{escape_html(org.name)}</b>\n\n"
        f"Категория: {escape_html(org.category)}\n\n"
        f"{escape_html(org.description or '—')}"
    )
    if org.link:
        text += f"\n\n🔗 {escape_html(org.link)}"
    text += f"\n\nВидимость: {'👁 показывается студентам' if org.is_active else '🚫 скрыто от студентов'}"
    return text


@router.callback_query(AdminMenuCB.filter(F.target == "content_orgs"))
async def cb_categories(callback: CallbackQuery, session: AsyncSession) -> None:
    categories = await crud.list_org_category_representatives(session, only_active=False)
    text = "🤝 <b>Студенческие организации</b>\n\n" + (
        "Категорий пока нет. Добавьте первую организацию." if not categories else "Выберите категорию:"
    )
    await callback.message.edit_text(text, reply_markup=orgs_categories_admin_kb(categories), parse_mode="HTML")
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "choose_cat"))
async def cb_category_items(callback: CallbackQuery, callback_data: OrgAdminCB, session: AsyncSession) -> None:
    representative = await crud.get_organization(session, callback_data.org_id)
    if representative is None:
        await callback.answer("Категория больше не существует.", show_alert=True)
        return
    items = await crud.list_organizations(
        session,
        category=representative.category,
        only_active=False,
    )
    text = f"🤝 <b>{escape_html(representative.category)}</b>\n\nВыберите организацию:"
    await callback.message.edit_text(
        text, reply_markup=orgs_list_admin_kb(items), parse_mode="HTML"
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
    organization = await crud.get_organization(session, callback_data.org_id)
    if organization is None:
        await callback.answer("Организация не найдена.", show_alert=True)
        return
    category = organization.category
    ok = await crud.delete_organization(session, organization.id)
    items = await crud.list_organizations(session, category=category, only_active=False)
    if items:
        reply_markup = orgs_list_admin_kb(items)
    else:
        categories = await crud.list_org_category_representatives(session, only_active=False)
        reply_markup = orgs_categories_admin_kb(categories)
    await callback.message.edit_text(
        "🗑 Организация удалена." if ok else "Не удалось удалить.",
        reply_markup=reply_markup,
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
    await callback.message.edit_text(
        f"✏️ Что изменить у «{escape_html(org.name)}»?",
        reply_markup=org_edit_menu_kb(org),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "edit_field"))
async def cb_edit_field_start(
    callback: CallbackQuery,
    callback_data: OrgAdminCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback_data.field not in FIELD_LABELS:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return
    organization = await crud.get_organization(session, callback_data.org_id)
    if organization is None:
        await callback.answer("Комитет не найден.", show_alert=True)
        return
    await state.set_state(OrganizationEditForm.entering_value)
    await state.update_data(org_id=callback_data.org_id, field=callback_data.field)
    label = FIELD_LABELS.get(callback_data.field, callback_data.field)
    if callback_data.field == "description":
        current_text = escape_html(organization.description or "Текст пока не добавлен")
        prompt = (
            f"📝 <b>{escape_html(organization.name)}</b>\n\n"
            f"Текущий текст:\n{current_text}\n\n"
            "Отправьте новый текст одним сообщением."
        )
    else:
        prompt = f"Введите новое значение поля «{label}»:"
        if callback_data.field == "link":
            prompt += "\nОтправьте «-», чтобы удалить ссылку."
    await callback.message.edit_text(
        prompt,
        reply_markup=form_control_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "clear_text"))
async def cb_clear_text(
    callback: CallbackQuery,
    callback_data: OrgAdminCB,
    session: AsyncSession,
) -> None:
    organization = await crud.get_organization(session, callback_data.org_id)
    if organization is None:
        await callback.answer("Комитет не найден.", show_alert=True)
        return
    if not organization.description:
        await callback.answer("Текст уже пуст.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Удалить только текст у «{escape_html(organization.name)}»?\n\n"
        "Сам комитет останется в списке.",
        reply_markup=org_clear_text_confirm_kb(organization.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrgAdminCB.filter(F.action == "clear_text_confirm"))
async def cb_clear_text_confirm(
    callback: CallbackQuery,
    callback_data: OrgAdminCB,
    session: AsyncSession,
) -> None:
    organization = await crud.update_organization(
        session,
        callback_data.org_id,
        description=None,
    )
    if organization is None:
        await callback.answer("Комитет не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        _detail_text(organization),
        reply_markup=org_detail_admin_kb(organization),
        parse_mode="HTML",
    )
    await callback.answer("Текст удалён")


@router.message(OrganizationEditForm.entering_value, F.text)
async def edit_field_receive_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    value = message.text.strip()
    if not value:
        await message.answer("Значение не может быть пустым.")
        return
    max_length = FIELD_MAX_LENGTHS[data["field"]]
    if len(value) > max_length:
        await message.answer(
            f"⚠️ Значение слишком длинное. Максимум — {max_length} символов."
        )
        return
    if data["field"] == "description" and value == "-":
        value = ""
    elif data["field"] == "link":
        normalized = _normalize_link(value)
        if normalized is None and value != "-":
            await message.answer("⚠️ Введите корректную ссылку или «-», чтобы удалить её.")
            return
        if normalized and len(normalized) > FIELD_MAX_LENGTHS["link"]:
            await message.answer("⚠️ Ссылка слишком длинная. Максимум — 255 символов.")
            return
        value = normalized or ""
    await state.update_data(new_value=value)
    await state.set_state(OrganizationEditForm.preview)
    label = FIELD_LABELS.get(data["field"], data["field"])
    await message.answer(
        f"Предпросмотр — {label}:\n\n{escape_html(value or '—')}",
        reply_markup=form_preview_kb(),
        parse_mode="HTML",
    )


@router.callback_query(StateFilter(OrganizationForm, OrganizationEditForm), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("OrganizationForm"):
        await state.clear()
        categories = await crud.list_org_category_representatives(session, only_active=False)
        await callback.message.edit_text("❌ Добавление отменено.", reply_markup=orgs_categories_admin_kb(categories))
        await callback.answer()
    elif current_state.startswith("OrganizationEditForm"):
        data = await state.get_data()
        await state.clear()
        org = await crud.get_organization(session, data.get("org_id"))
        await callback.answer("Отменено")
        if org:
            await callback.message.edit_text(
                _detail_text(org),
                reply_markup=org_detail_admin_kb(org),
                parse_mode="HTML",
            )


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
    await callback.message.edit_text(
        _detail_text(org),
        reply_markup=org_detail_admin_kb(org),
        parse_mode="HTML",
    )


# ---------------------------- Добавление ---------------------------------

@router.callback_query(OrgAdminCB.filter(F.action == "add"))
async def cb_add_start(
    callback: CallbackQuery,
    callback_data: OrgAdminCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    representative = (
        await crud.get_organization(session, callback_data.org_id)
        if callback_data.org_id
        else None
    )
    if representative is not None:
        await state.update_data(category=representative.category)
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
    category = message.text.strip()
    if not category:
        await message.answer("⚠️ Категория не может быть пустой.")
        return
    if len(category) > FIELD_MAX_LENGTHS["category"]:
        await message.answer("⚠️ Название категории не должно превышать 64 символа.")
        return
    await state.update_data(category=category)
    await state.set_state(OrganizationForm.entering_name)
    await message.answer("Введите название организации:", reply_markup=form_control_kb())


@router.message(OrganizationForm.entering_name, F.text)
async def add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Название не может быть пустым.")
        return
    if len(name) > FIELD_MAX_LENGTHS["name"]:
        await message.answer("⚠️ Название не должно превышать 255 символов.")
        return
    await state.update_data(name=name)
    await state.set_state(OrganizationForm.entering_description)
    await message.answer(
        "Введите краткое описание или «-», если пропустить:", reply_markup=form_control_kb()
    )


@router.message(OrganizationForm.entering_description, F.text)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = None if message.text.strip() == "-" else message.text.strip()
    if desc and len(desc) > MAX_ORGANIZATION_TEXT_LENGTH:
        await message.answer(
            f"⚠️ Описание слишком длинное. Максимум — {MAX_ORGANIZATION_TEXT_LENGTH} символов."
        )
        return
    await state.update_data(description=desc)
    await state.set_state(OrganizationForm.entering_link)
    await message.answer(
        "Введите ссылку (Telegram/VK и т.п.) или «-», если пропустить:", reply_markup=form_control_kb()
    )


@router.message(OrganizationForm.entering_link, F.text)
async def add_link(message: Message, state: FSMContext) -> None:
    raw_link = message.text.strip()
    link = _normalize_link(raw_link)
    if link is None and raw_link != "-":
        await message.answer("⚠️ Введите корректную ссылку или «-», если её нет.")
        return
    if link and len(link) > 255:
        await message.answer("⚠️ Ссылка слишком длинная. Максимум — 255 символов.")
        return
    await state.update_data(link=link)
    await state.set_state(OrganizationForm.preview)
    data = await state.get_data()
    text = (
        "Предпросмотр:\n\n"
        f"Категория: {escape_html(data['category'])}\n"
        f"Название: {escape_html(data['name'])}\n"
        f"Описание: {escape_html(data.get('description') or '—')}\n"
        f"Ссылка: {escape_html(data.get('link') or '—')}"
    )
    await message.answer(text, reply_markup=form_preview_kb(), parse_mode="HTML")


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
        "✅ Организация добавлена.", reply_markup=orgs_list_admin_kb(items)
    )
    await callback.answer()


@router.callback_query(
    F.data.regexp(r"^orgadm:[^:]*:[^:]*:[^:]*:[^:]*$")
)
async def cb_legacy_organization_button(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Заменить устаревшие кнопки организаций актуальным меню.

    До перехода на короткие числовые callback старые сообщения содержали
    название категории внутри callback_data. После обновления такие кнопки
    больше не соответствуют новой схеме и без fallback выглядели сломанными.
    """
    await state.clear()
    categories = await crud.list_org_category_representatives(
        session,
        only_active=False,
    )
    text = "🤝 <b>Студенческие организации</b>\n\n" + (
        "Категорий пока нет. Добавьте первую организацию."
        if not categories
        else "Кнопки обновлены. Выберите категорию:"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=orgs_categories_admin_kb(categories),
            parse_mode="HTML",
        )
        answer_text = "Старая кнопка заменена — выберите раздел ещё раз"
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
        answer_text = "Это старая кнопка — заново откройте /admin"
    await callback.answer(answer_text)
