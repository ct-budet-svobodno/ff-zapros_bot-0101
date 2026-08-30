"""/start, /menu и базовая навигация по главному меню."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user
from keyboards.common_kb import main_menu_kb
from utils.callback_data import MenuCB

router = Router(name="user_start")

WELCOME_TEXT = (
    "👋 Добро пожаловать в бота Финансового факультета Финансового университета!\n\n"
    "Здесь вы можете узнать о факультете и Студенческом совете, получить нужные "
    "документы и задать вопрос ответственным сотрудникам.\n\n"
    "Выберите раздел в меню ниже 👇"
)


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await get_or_create_user(
        session, message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("menu"), F.chat.type == "private")
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏠 Главное меню:", reply_markup=main_menu_kb())


@router.callback_query(
    MenuCB.filter(F.target == "home_inline"),
    F.message.chat.type == "private",
)
async def cb_home_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(
    MenuCB.filter(F.target == "home"),
    F.message.chat.type == "private",
)
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    # Используется как "Назад" из разделов первого уровня (например, "О факультете")
    await cb_home_inline(callback, state)
