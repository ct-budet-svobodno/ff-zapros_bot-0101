"""
Управление документацией (ТЗ, раздел 29): добавление/редактирование/замена/
удаление PDF-документов. PDF хранится по Telegram file_id — этого достаточно,
т.к. Telegram кеширует файл и повторная загрузка не нужна (см. README,
раздел "Хранение файлов").
"""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import doc_detail_admin_kb, docs_list_admin_kb, form_control_kb, form_preview_kb
from states.states import DocumentEdit, DocumentForm
from utils.admin_filter import IsAdmin
from utils.callback_data import AdminMenuCB, DocAdminCB, FormControlCB

router = Router(name="admin_documents")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(AdminMenuCB.filter(F.target == "docs"))
async def cb_list(callback: CallbackQuery, session: AsyncSession) -> None:
    documents = await crud.list_documents(session, only_active=False)
    text = "📚 <b>Управление документацией</b>\n\n" + ("Документов пока нет." if not documents else "Выберите документ:")
    await callback.message.edit_text(text, reply_markup=docs_list_admin_kb(documents), parse_mode="HTML")
    await callback.answer()


@router.callback_query(DocAdminCB.filter(F.action == "list"))
async def cb_list_back(callback: CallbackQuery, session: AsyncSession) -> None:
    await cb_list(callback, session)


@router.callback_query(DocAdminCB.filter(F.action == "view"))
async def cb_view(callback: CallbackQuery, callback_data: DocAdminCB, session: AsyncSession) -> None:
    document = await crud.get_document(session, callback_data.doc_id)
    if not document:
        await callback.answer("Не найдено.", show_alert=True)
        return
    text = f"📄 <b>{document.title}</b>\n\n{document.description or '—'}"
    await callback.message.edit_text(text, reply_markup=doc_detail_admin_kb(document.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(DocAdminCB.filter(F.action == "delete"))
async def cb_delete(callback: CallbackQuery, callback_data: DocAdminCB, session: AsyncSession) -> None:
    ok = await crud.delete_document(session, callback_data.doc_id)
    documents = await crud.list_documents(session, only_active=False)
    await callback.message.edit_text(
        "🗑 Документ удалён." if ok else "Не удалось удалить.", reply_markup=docs_list_admin_kb(documents)
    )
    await callback.answer()


# ---------------------------- Добавление -----------------------------------

@router.callback_query(DocAdminCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DocumentForm.entering_title)
    await callback.message.edit_text("Введите название документа:", reply_markup=form_control_kb())
    await callback.answer()


@router.callback_query(StateFilter(DocumentForm, DocumentEdit), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if current_state.startswith("DocumentForm"):
        await state.clear()
        documents = await crud.list_documents(session, only_active=False)
        await callback.message.edit_text("❌ Добавление отменено.", reply_markup=docs_list_admin_kb(documents))
        await callback.answer()
    elif current_state.startswith("DocumentEdit"):
        data = await state.get_data()
        await state.clear()
        document = await crud.get_document(session, data.get("doc_id"))
        if document:
            await callback.message.edit_text(
                f"📄 <b>{document.title}</b>\n\n{document.description or '—'}",
                reply_markup=doc_detail_admin_kb(document.id),
                parse_mode="HTML",
            )
        await callback.answer("Отменено")


@router.message(DocumentForm.entering_title, F.text)
async def add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(DocumentForm.entering_description)
    await message.answer("Введите краткое описание документа:", reply_markup=form_control_kb())


@router.message(DocumentForm.entering_description, F.text)
async def add_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(DocumentForm.uploading_pdf)
    await message.answer("Загрузите PDF-файл документа:", reply_markup=form_control_kb())


@router.message(DocumentForm.uploading_pdf, F.document)
async def add_pdf(message: Message, state: FSMContext) -> None:
    doc = message.document
    if doc.mime_type != "application/pdf" and not (doc.file_name or "").lower().endswith(".pdf"):
        await message.answer("⚠️ Пожалуйста, загрузите файл в формате PDF.")
        return
    await state.update_data(file_id=doc.file_id, file_name=doc.file_name)
    data = await state.get_data()
    await state.set_state(DocumentForm.preview)
    text = f"Предпросмотр:\n\n📄 {data['title']}\n{data['description']}\n\nФайл: {doc.file_name}"
    await message.answer(text, reply_markup=form_preview_kb())


@router.message(DocumentForm.uploading_pdf)
async def add_pdf_wrong(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте PDF-файл документом (не фото).")


@router.callback_query(DocumentForm.preview, FormControlCB.filter(F.action == "save"))
async def add_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await crud.add_document(
        session,
        title=data["title"],
        description=data["description"],
        file_id=data["file_id"],
        file_name=data.get("file_name"),
    )
    await state.clear()
    documents = await crud.list_documents(session, only_active=False)
    await callback.message.edit_text("✅ Документ добавлен.", reply_markup=docs_list_admin_kb(documents))
    await callback.answer()


# ---------------------------- Редактирование --------------------------------

@router.callback_query(DocAdminCB.filter(F.action == "edit_title"))
async def cb_edit_title_start(callback: CallbackQuery, callback_data: DocAdminCB, state: FSMContext) -> None:
    await state.set_state(DocumentEdit.entering_title)
    await state.update_data(doc_id=callback_data.doc_id)
    await callback.message.edit_text("Введите новое название документа:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(DocumentEdit.entering_title, F.text)
async def edit_title_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    document = await crud.update_document(session, data["doc_id"], title=message.text.strip())
    await state.clear()
    if document:
        await message.answer(
            f"✅ Название обновлено.\n\n📄 <b>{document.title}</b>\n\n{document.description or '—'}",
            reply_markup=doc_detail_admin_kb(document.id),
            parse_mode="HTML",
        )


@router.callback_query(DocAdminCB.filter(F.action == "edit_desc"))
async def cb_edit_desc_start(callback: CallbackQuery, callback_data: DocAdminCB, state: FSMContext) -> None:
    await state.set_state(DocumentEdit.entering_description)
    await state.update_data(doc_id=callback_data.doc_id)
    await callback.message.edit_text("Введите новое описание документа:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(DocumentEdit.entering_description, F.text)
async def edit_desc_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    document = await crud.update_document(session, data["doc_id"], description=message.text.strip())
    await state.clear()
    if document:
        await message.answer(
            f"✅ Описание обновлено.\n\n📄 <b>{document.title}</b>\n\n{document.description or '—'}",
            reply_markup=doc_detail_admin_kb(document.id),
            parse_mode="HTML",
        )


@router.callback_query(DocAdminCB.filter(F.action == "edit_file"))
async def cb_edit_file_start(callback: CallbackQuery, callback_data: DocAdminCB, state: FSMContext) -> None:
    await state.set_state(DocumentEdit.uploading_pdf)
    await state.update_data(doc_id=callback_data.doc_id)
    await callback.message.edit_text("Загрузите новый PDF-файл:", reply_markup=form_control_kb())
    await callback.answer()


@router.message(DocumentEdit.uploading_pdf, F.document)
async def edit_file_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    doc = message.document
    if doc.mime_type != "application/pdf" and not (doc.file_name or "").lower().endswith(".pdf"):
        await message.answer("⚠️ Пожалуйста, загрузите файл в формате PDF.")
        return
    data = await state.get_data()
    document = await crud.update_document(session, data["doc_id"], file_id=doc.file_id, file_name=doc.file_name)
    await state.clear()
    if document:
        await message.answer(
            f"✅ Файл документа обновлён.\n\n📄 <b>{document.title}</b>",
            reply_markup=doc_detail_admin_kb(document.id),
            parse_mode="HTML",
        )


@router.message(DocumentEdit.uploading_pdf)
async def edit_file_wrong(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте PDF-файл документом.")
