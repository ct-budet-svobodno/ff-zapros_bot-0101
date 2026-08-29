"""
Общие переиспользуемые элементы клавиатур: "Назад" / "Главное меню",
а также reply-клавиатура главного меню.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from utils.callback_data import MenuCB

BTN_ABOUT = "🏛 О факультете"
BTN_COUNCIL = "🎓 Студенческий совет"
BTN_DOCS = "📚 Документация"
BTN_ASK = "📨 Задать вопрос"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ABOUT), KeyboardButton(text=BTN_COUNCIL)],
            [KeyboardButton(text=BTN_DOCS), KeyboardButton(text=BTN_ASK)],
        ],
        resize_keyboard=True,
    )


def nav_row(back_target: str | None = "home", include_home: bool = True) -> list[InlineKeyboardButton]:
    """Строка с кнопками "Назад" и "Главное меню" для inline-клавиатур."""
    row = []
    if back_target:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuCB(target=back_target).pack()))
    if include_home:
        row.append(InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCB(target="home_inline").pack()))
    return row


def kb_with_nav(rows: list[list[InlineKeyboardButton]], back_target: str | None = "home",
                 include_home: bool = True) -> InlineKeyboardMarkup:
    all_rows = list(rows)
    nav = nav_row(back_target, include_home)
    if nav:
        all_rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=all_rows)


def cancel_kb(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data=callback_data)]]
    )
