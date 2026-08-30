"""
Точка входа в админ-панель. Проверка прав — через фильтр IsAdmin,
применяемый на уровне роутера (см. main.py, router.message.filter(IsAdmin())
для этого роутера) и повторно на каждом callback этого модуля.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import admin_main_menu_kb, content_management_kb, requests_menu_admin_kb
from utils.admin_filter import NOT_ADMIN_TEXT, IsAdmin
from utils.callback_data import AdminMenuCB

router = Router(name="admin_panel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

ADMIN_PANEL_TEXT = "🔐 Панель администратора"


@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_PANEL_TEXT, reply_markup=admin_main_menu_kb())


@router.callback_query(AdminMenuCB.filter(F.target == "root"))
async def cb_admin_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(ADMIN_PANEL_TEXT, reply_markup=admin_main_menu_kb())
    await callback.answer()


@router.callback_query(AdminMenuCB.filter(F.target == "content"))
async def cb_content_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Управление информацией</b>\n\nВыберите раздел:",
        reply_markup=content_management_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminMenuCB.filter(F.target == "requests"))
async def cb_requests_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    stats = await crud.get_requests_stats(session)
    text = (
        "📨 <b>Обращения студентов</b>\n\n"
        "Новые обращения приходят в рабочую группу с кнопкой «💬 Ответить».\n\n"
        f"Всего обращений: {stats['total']}\n"
        f"🆕 Новых: {stats['new']}\n"
        f"🔄 В работе: {stats['in_progress']}\n"
        f"✅ Закрыто: {stats['closed']}"
    )
    await callback.message.edit_text(text, reply_markup=requests_menu_admin_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminMenuCB.filter(F.target == "requests_stats"))
async def cb_requests_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    stats = await crud.get_requests_stats(session)
    text = (
        "📊 <b>Статистика обращений</b>\n\n"
        f"Всего: {stats['total']}\n"
        f"🆕 Новых: {stats['new']}\n"
        f"🔄 В работе: {stats['in_progress']}\n"
        f"✅ Закрыто: {stats['closed']}\n\n"
        f"🕶 Анонимных: {stats['anonymous']}\n"
        f"👤 Неанонимных: {stats['non_anonymous']}"
    )
    from keyboards.admin_kb import admin_back_kb
    await callback.message.edit_text(text, reply_markup=admin_back_kb("requests"), parse_mode="HTML")
    await callback.answer()


# Единая заглушка на случай, если обычный пользователь всё же вызовет /admin
# (сюда попадёт, только если IsAdmin вернул False — Router.message с фильтром
# просто не пропустит апдейт дальше по цепочке; финальный ответ формирует
# fallback-хендлер в main-роутере, см. handlers/user/fallback.py)
