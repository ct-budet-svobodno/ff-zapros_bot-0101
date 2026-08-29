from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.common_kb import BTN_COUNCIL
from keyboards.user_kb import council_menu_kb, digests_kb, leaders_kb, media_kb
from utils.callback_data import DigestItemCB, LeaderAdminCB, MenuCB

router = Router(name="user_council")

PLACEHOLDER_EMPTY = "Информация пока не добавлена администратором. Загляните позже 🙂"


@router.message(F.text == BTN_COUNCIL)
async def show_council(message: Message, session: AsyncSession) -> None:
    section = await crud.get_section(session, "council_info")
    text = section.body if section else PLACEHOLDER_EMPTY
    await message.answer(f"🎓 <b>Студенческий совет</b>\n\n{text}", reply_markup=council_menu_kb(), parse_mode="HTML")


@router.callback_query(MenuCB.filter(F.target == "council"))
async def cb_council(callback: CallbackQuery, session: AsyncSession) -> None:
    section = await crud.get_section(session, "council_info")
    text = section.body if section else PLACEHOLDER_EMPTY
    await callback.message.edit_text(
        f"🎓 <b>Студенческий совет</b>\n\n{text}", reply_markup=council_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "leaders"))
async def cb_leaders(callback: CallbackQuery, session: AsyncSession) -> None:
    leaders = await crud.list_council_leaders(session)
    if not leaders:
        await callback.message.edit_text(
            f"👥 <b>Руководители Студенческого совета</b>\n\n{PLACEHOLDER_EMPTY}",
            reply_markup=leaders_kb([]),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "👥 <b>Руководители Студенческого совета</b>\n\nВыберите руководителя:",
            reply_markup=leaders_kb(leaders),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(LeaderAdminCB.filter(F.action == "view"))
async def cb_leader_detail(callback: CallbackQuery, callback_data: LeaderAdminCB, session: AsyncSession) -> None:
    leader = await crud.get_council_leader(session, callback_data.leader_id)
    if not leader:
        await callback.answer("Информация не найдена.", show_alert=True)
        return
    lines = [f"👤 <b>{leader.full_name}</b>", leader.position]
    if leader.telegram_username:
        lines.append(f"Telegram: @{leader.telegram_username}")
    text = "\n".join(lines)
    if leader.photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=leader.photo_file_id, caption=text, reply_markup=leaders_kb([leader]), parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(text, reply_markup=leaders_kb([leader]), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "digests"))
async def cb_digests(callback: CallbackQuery, session: AsyncSession) -> None:
    digests = await crud.list_digests(session)
    if not digests:
        await callback.message.edit_text(
            f"📅 <b>Дайджест мероприятий</b>\n\n{PLACEHOLDER_EMPTY}",
            reply_markup=digests_kb([]),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "📅 <b>Дайджест мероприятий</b>\n\nВыберите месяц:",
            reply_markup=digests_kb(digests),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(DigestItemCB.filter())
async def cb_digest_item(callback: CallbackQuery, callback_data: DigestItemCB, session: AsyncSession) -> None:
    digest = await crud.get_digest(session, callback_data.digest_id)
    if not digest:
        await callback.answer("Дайджест не найден.", show_alert=True)
        return
    text = f"📅 <b>{digest.title}</b> ({digest.month_label})\n\n{digest.text}"
    from keyboards.common_kb import kb_with_nav
    await callback.message.edit_text(
        text, reply_markup=kb_with_nav([], back_target="digests"), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "selection"))
async def cb_selection(callback: CallbackQuery, session: AsyncSession) -> None:
    section = await crud.get_section(session, "council_selection")
    text = section.body if section else PLACEHOLDER_EMPTY
    from keyboards.common_kb import kb_with_nav
    await callback.message.edit_text(
        f"📝 <b>Отбор в Студенческий совет</b>\n\n{text}",
        reply_markup=kb_with_nav([], back_target="council"),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.target == "media"))
async def cb_media(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📱 <b>Медиа Финансового факультета</b>\n\nВыберите ресурс:",
        reply_markup=media_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
