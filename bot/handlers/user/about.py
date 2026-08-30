from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.common_kb import BTN_ABOUT
from keyboards.user_kb import (
    about_faculty_kb,
    faculty_admins_kb,
    org_categories_kb,
    org_item_detail_kb,
    org_items_kb,
)
from utils.callback_data import FacultyAdminCB, MenuCB, OrgCategoryCB, OrgItemCB

router = Router(name="user_about")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

PLACEHOLDER_EMPTY = "Информация пока не добавлена администратором. Загляните позже 🙂"


@router.message(F.text == BTN_ABOUT)
async def show_about(message: Message, session: AsyncSession) -> None:
    section = await crud.get_section(session, "faculty_history")
    text = section.body if section else PLACEHOLDER_EMPTY
    await message.answer(f"🏛 <b>О факультете</b>\n\n{text}", reply_markup=about_faculty_kb(), parse_mode="HTML")


@router.callback_query(MenuCB.filter(F.target == "about"))
async def cb_show_about(callback: CallbackQuery, session: AsyncSession) -> None:
    section = await crud.get_section(session, "faculty_history")
    text = section.body if section else PLACEHOLDER_EMPTY
    await callback.message.edit_text(
        f"🏛 <b>О факультете</b>\n\n{text}", reply_markup=about_faculty_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "faculty_admins"))
async def cb_faculty_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    people = await crud.list_faculty_admins(session)
    if not people:
        await callback.message.edit_text(
            f"👥 <b>Администрация факультета</b>\n\n{PLACEHOLDER_EMPTY}",
            reply_markup=faculty_admins_kb([]),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "👥 <b>Администрация факультета</b>\n\nВыберите представителя администрации:",
            reply_markup=faculty_admins_kb(people),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(FacultyAdminCB.filter(F.action == "view"))
async def cb_faculty_admin_detail(callback: CallbackQuery, callback_data: FacultyAdminCB, session: AsyncSession) -> None:
    person = await crud.get_faculty_admin(session, callback_data.person_id)
    if not person:
        await callback.answer("Информация не найдена.", show_alert=True)
        return
    lines = [f"👤 <b>{person.full_name}</b>", person.position]
    if person.contact_info:
        lines.append("")
        lines.append(person.contact_info)
    text = "\n".join(lines)
    if person.photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=person.photo_file_id, caption=text, reply_markup=faculty_admins_kb([person]), parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(text, reply_markup=faculty_admins_kb([person]), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "orgs"))
async def cb_orgs(callback: CallbackQuery, session: AsyncSession) -> None:
    categories = await crud.list_org_categories(session)
    if not categories:
        await callback.message.edit_text(
            f"🤝 <b>Студенческие организации</b>\n\n{PLACEHOLDER_EMPTY}",
            reply_markup=org_categories_kb([]),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "🤝 <b>Студенческие организации</b>\n\nВыберите категорию:",
            reply_markup=org_categories_kb(categories),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(OrgCategoryCB.filter())
async def cb_org_category(callback: CallbackQuery, callback_data: OrgCategoryCB, session: AsyncSession) -> None:
    items = await crud.list_organizations(session, category=callback_data.category)
    if not items:
        await callback.message.edit_text(
            f"🤝 <b>{callback_data.category}</b>\n\n{PLACEHOLDER_EMPTY}",
            reply_markup=org_items_kb([], callback_data.category),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"🤝 <b>{callback_data.category}</b>\n\nВыберите организацию:",
            reply_markup=org_items_kb(items, callback_data.category),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(OrgItemCB.filter())
async def cb_org_item(callback: CallbackQuery, callback_data: OrgItemCB, session: AsyncSession) -> None:
    org = await crud.get_organization(session, callback_data.org_id)
    if not org:
        await callback.answer("Организация не найдена.", show_alert=True)
        return
    text = f"🤝 <b>{org.name}</b>\n\n{org.description or PLACEHOLDER_EMPTY}"
    await callback.message.edit_text(text, reply_markup=org_item_detail_kb(org), parse_mode="HTML")
    await callback.answer()
