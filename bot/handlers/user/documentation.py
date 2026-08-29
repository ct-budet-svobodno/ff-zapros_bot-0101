from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.common_kb import BTN_DOCS
from keyboards.user_kb import documentation_kb
from utils.callback_data import DocItemCB, MenuCB

router = Router(name="user_documentation")

PLACEHOLDER_EMPTY = (
    "Документы пока не добавлены администратором. Загляните позже 🙂"
)


def _list_text(count: int) -> str:
    if count == 0:
        return f"📚 <b>Документация</b>\n\n{PLACEHOLDER_EMPTY}"
    return "📚 <b>Документация</b>\n\nВыберите документ, чтобы получить PDF:"


@router.message(F.text == BTN_DOCS)
async def show_docs(message: Message, session: AsyncSession) -> None:
    documents = await crud.list_documents(session)
    await message.answer(_list_text(len(documents)), reply_markup=documentation_kb(documents), parse_mode="HTML")


@router.callback_query(MenuCB.filter(F.target == "docs"))
async def cb_docs(callback: CallbackQuery, session: AsyncSession) -> None:
    documents = await crud.list_documents(session)
    await callback.message.edit_text(
        _list_text(len(documents)), reply_markup=documentation_kb(documents), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(DocItemCB.filter())
async def cb_doc_item(callback: CallbackQuery, callback_data: DocItemCB, session: AsyncSession) -> None:
    document = await crud.get_document(session, callback_data.doc_id)
    if not document:
        await callback.answer("Документ не найден.", show_alert=True)
        return
    caption = document.title
    if document.description:
        caption += f"\n\n{document.description}"
    try:
        await callback.message.answer_document(document=document.file_id, caption=caption)
    except TelegramAPIError:
        await callback.message.answer(
            "⚠️ Не удалось отправить документ. Попробуйте позже или обратитесь к администратору."
        )
    await callback.answer()
