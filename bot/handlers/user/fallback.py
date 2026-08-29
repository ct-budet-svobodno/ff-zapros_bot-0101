"""
Регистрируется ПОСЛЕДНИМ в диспетчере (см. main.py).

Обрабатывает:
  * /admin от пользователя без прав — единственное место, где формируется
    ответ "⛔ У вас нет доступа...", т.к. сам admin-роутер такие апдейты
    просто не пропускает (см. utils/admin_filter.IsAdmin);
  * любые "неожиданные" сообщения/callback'и, которые не подошли ни одному
    хендлеру — чтобы бот никогда не оставался немым (ТЗ, раздел 33).
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.common_kb import main_menu_kb
from utils.admin_filter import NOT_ADMIN_TEXT

router = Router(name="fallback")


@router.message(Command("admin"))
async def admin_denied(message: Message) -> None:
    await message.answer(NOT_ADMIN_TEXT)


@router.callback_query()
async def unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer("⚠️ Это действие больше не доступно. Откройте меню заново: /menu", show_alert=True)


@router.message()
async def unhandled_message(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state:
        # Пользователь застрял в незавершённом сценарии — не молчим, а подсказываем.
        await message.answer(
            "⚠️ Не совсем понял ваше сообщение в текущем шаге. "
            "Пожалуйста, используйте кнопки выше, либо отправьте /menu, чтобы начать заново."
        )
        return
    await message.answer(
        "🤔 Не совсем понял ваш запрос. Пожалуйста, воспользуйтесь меню ниже.",
        reply_markup=main_menu_kb(),
    )
