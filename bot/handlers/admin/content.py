"""
Редактирование "длинных" текстовых материалов (ContentSection):
история факультета, инфо о Студсовете, текст об отборе.

Сценарий (ТЗ, раздел 6):
Управление информацией -> выбор раздела -> выбор материала -> Изменить ->
бот просит текст -> админ отправляет -> предпросмотр -> Сохранить/Отменить.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import ContentSection
from keyboards.admin_kb import section_detail_kb, section_preview_kb, sections_list_kb
from states.states import SectionEdit
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, SectionCB, SectionPreviewCB

router = Router(name="admin_content_sections")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

# Порядок и подписи для раздела "Тексты" в админке
SECTION_KEYS = [
    ("faculty_history", "История факультета"),
    ("council_info", "О Студенческом совете"),
    ("council_selection", "Отбор в Студенческий совет"),
]


@router.callback_query(AdminMenuCB.filter(F.target == "content_sections"))
async def cb_sections_list(callback: CallbackQuery, session: AsyncSession) -> None:
    sections = []
    for key, title in SECTION_KEYS:
        section = await crud.get_section(session, key)
        if not section:
            # На случай, если seed не запускали — создаём пустую заготовку.
            section = ContentSection(key=key, title=title, body="(текст ещё не задан)")
            session.add(section)
            await session.commit()
            await session.refresh(section)
        sections.append(section)
    await callback.message.edit_text(
        "📖 <b>Тексты</b>\n\nВыберите материал для просмотра/редактирования:",
        reply_markup=sections_list_kb(sections),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SectionCB.filter(F.action == "view"))
async def cb_section_view(callback: CallbackQuery, callback_data: SectionCB, session: AsyncSession) -> None:
    section = await crud.get_section(session, callback_data.key)
    if not section:
        await callback.answer("Раздел не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📖 <b>{section.title}</b>\n\n{section.body}",
        reply_markup=section_detail_kb(section.key),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SectionCB.filter(F.action == "edit"))
async def cb_section_edit_start(
    callback: CallbackQuery, callback_data: SectionCB, state: FSMContext
) -> None:
    await state.set_state(SectionEdit.entering_text)
    await state.update_data(section_key=callback_data.key)
    await callback.message.edit_text(
        "✏️ Отправьте новый текст для этого раздела одним сообщением.\n\n"
        "Можно использовать обычные переносы строк — форматирование сохранится."
    )
    await callback.answer()


@router.message(SectionEdit.entering_text, F.text)
async def section_edit_receive_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("Текст не может быть пустым. Отправьте текст раздела.")
        return
    await state.update_data(new_body=text)
    await state.set_state(SectionEdit.preview)
    data = await state.get_data()
    await message.answer(
        f"Предпросмотр:\n\n{text}",
        reply_markup=section_preview_kb(data["section_key"]),
    )


@router.message(SectionEdit.entering_text)
async def section_edit_wrong_type(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте новый текст сообщением (только текст).")


@router.callback_query(SectionEdit.preview, SectionPreviewCB.filter(F.action == "cancel"))
async def section_edit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Изменение отменено.")
    await callback.answer()


@router.callback_query(SectionEdit.preview, SectionPreviewCB.filter(F.action == "save"))
async def section_edit_save(
    callback: CallbackQuery, callback_data: SectionPreviewCB, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    section = await crud.update_section_body(session, data["section_key"], data["new_body"])
    await state.clear()
    if section:
        await callback.message.edit_text(
            f"✅ Раздел «{section.title}» обновлён.",
            reply_markup=section_detail_kb(section.key),
        )
    else:
        await callback.message.edit_text("⚠️ Не удалось сохранить изменения — раздел не найден.")
    await callback.answer("Сохранено")
