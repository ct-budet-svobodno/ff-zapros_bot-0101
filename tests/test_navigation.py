"""Проверки навигации без Telegram API и без рабочей базы данных."""
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))

with patch.dict(os.environ, {
    "BOT_TOKEN": "123456:TEST",
    "WORK_GROUP_ID": "-100123456",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}):
    from handlers.admin import faculty_admins, leaders, panel
    from handlers.user import about, council, start

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, PhotoSize, Update, User
from keyboards.common_kb import main_menu_kb
from keyboards.user_kb import faculty_admin_detail_kb, leader_detail_kb
from utils.callback_data import MenuCB
from utils.navigation import show_text_screen


def message_mock(text=None):
    return SimpleNamespace(
        text=text,
        edit_text=AsyncMock(),
        answer=AsyncMock(),
        delete=AsyncMock(),
    )


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_is_edited(self):
        message = message_mock("old menu")
        await show_text_screen(message, "new menu")
        message.edit_text.assert_awaited_once()
        message.answer.assert_not_awaited()
        message.delete.assert_not_awaited()

    async def test_photo_is_replaced_only_after_sending_menu(self):
        message = message_mock()
        order = []
        message.answer.side_effect = lambda *a, **kw: order.append("send")
        message.delete.side_effect = lambda: order.append("delete")
        await show_text_screen(message, "new menu")
        message.edit_text.assert_not_awaited()
        self.assertEqual(order, ["send", "delete"])

    async def test_failed_send_keeps_original_card(self):
        message = message_mock()
        message.answer.side_effect = RuntimeError("send failed")
        with self.assertRaises(RuntimeError):
            await show_text_screen(message, "new menu")
        message.delete.assert_not_awaited()

    async def test_home_keyboard_sends_new_message(self):
        message = message_mock("text card")
        await show_text_screen(message, "Home", reply_markup=main_menu_kb())
        message.edit_text.assert_not_awaited()
        message.answer.assert_awaited_once()

    async def test_repeated_back_does_not_raise(self):
        message = message_mock("same menu")
        message.edit_text.side_effect = TelegramBadRequest(
            method=EditMessageText(chat_id=1, message_id=1, text="same menu"),
            message="Bad Request: message is not modified",
        )
        await show_text_screen(message, "same menu")
        message.answer.assert_not_awaited()

    async def test_old_card_deletion_failure_keeps_new_menu(self):
        message = message_mock()
        message.delete.side_effect = TelegramBadRequest(
            method=EditMessageText(chat_id=1, message_id=1, text="menu"),
            message="Bad Request: message can't be deleted",
        )
        await show_text_screen(message, "new menu")
        message.answer.assert_awaited_once()

    async def test_unexpected_telegram_errors_are_not_swallowed(self):
        message = message_mock("text")
        message.edit_text.side_effect = TelegramBadRequest(
            method=EditMessageText(chat_id=1, message_id=1, text="menu"),
            message="Bad Request: can't parse entities",
        )
        with self.assertRaises(TelegramBadRequest):
            await show_text_screen(message, "menu")

    async def test_admin_back_from_photos(self):
        for handler, query in (
            (faculty_admins.cb_list_back, "list_faculty_admins"),
            (leaders.cb_list_back, "list_council_leaders"),
        ):
            with self.subTest(handler=handler.__name__, query=query):
                callback = SimpleNamespace(message=message_mock(), answer=AsyncMock())
                with patch("database.crud." + query, new=AsyncMock(return_value=[])):
                    await handler(callback, session=object())
                callback.message.edit_text.assert_not_awaited()
                callback.message.answer.assert_awaited_once()
                callback.answer.assert_awaited_once()

    async def test_admin_content_back_from_photo(self):
        callback = SimpleNamespace(message=message_mock(), answer=AsyncMock())
        state = SimpleNamespace(clear=AsyncMock())
        await panel.cb_content_menu(callback, state)
        callback.message.answer.assert_awaited_once()
        state.clear.assert_awaited_once()

    def test_detail_buttons_go_to_parent_list(self):
        for keyboard, target in (
            (faculty_admin_detail_kb(), "faculty_admins"),
            (leader_detail_kb(), "leaders"),
        ):
            buttons = [button for row in keyboard.inline_keyboard for button in row]
            back = next(button for button in buttons if button.text == "⬅️ Назад")
            self.assertEqual(MenuCB.unpack(back.callback_data).target, target)
            self.assertEqual(len(buttons), 2)  # Назад и Главное меню, без повтора карточки.


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.source_has_photo = False

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        if False:
            yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, EditMessageText) and self.source_has_photo:
            raise TelegramBadRequest(
                method=method, message="Bad Request: there is no text in the message to edit"
            )
        if isinstance(method, (SendMessage, EditMessageText)):
            return Message(
                message_id=100, date=0, chat=Chat(id=1, type="private"), text=method.text,
            )
        return True


class DispatcherNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_back_callbacks_from_text_and_photo(self):
        api = RecordingSession()
        bot = Bot(token="123456:TEST", session=api)
        dp = Dispatcher()
        dp.include_routers(start.router, about.router, council.router)
        try:
            with (
                patch("database.crud.list_faculty_admins", new=AsyncMock(return_value=[])),
                patch("database.crud.list_council_leaders", new=AsyncMock(return_value=[])),
                patch("database.crud.get_section", new=AsyncMock(return_value=None)),
            ):
                # about/council также покрывают кнопки на карточках до обновления.
                for target in ("faculty_admins", "leaders", "about", "council", "home", "home_inline"):
                    for photo in (False, True):
                        with self.subTest(target=target, photo=photo):
                            api.calls.clear()
                            api.source_has_photo = photo
                            message = Message(
                                message_id=1, date=0, chat=Chat(id=1, type="private"),
                                text=None if photo else "card",
                                photo=[PhotoSize(file_id="x", file_unique_id="y", width=1, height=1)] if photo else None,
                            )
                            callback = CallbackQuery(
                                id="test", from_user=User(id=1, is_bot=False, first_name="Test"),
                                chat_instance="test", message=message,
                                data=MenuCB(target=target).pack(),
                            )
                            await dp.feed_update(bot, Update(update_id=1, callback_query=callback), session=object())
                            self.assertTrue(any(isinstance(call, (SendMessage, EditMessageText)) for call in api.calls))
                            if photo:
                                self.assertFalse(any(isinstance(call, EditMessageText) for call in api.calls))
        finally:
            await dp.storage.close()
            await bot.session.close()


if __name__ == "__main__":
    unittest.main()
