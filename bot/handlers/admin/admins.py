"""Управление обычными администраторами, доступное только суперадмину."""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin_kb import admin_delete_confirm_kb, admins_list_kb, form_control_kb
from states.states import AdminManageForm
from utils.admin_filter import IsSuperAdmin
from utils.callback_data import AdminManageCB, AdminMenuCB, FormControlCB

router = Router(name="admin_admins")
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


def _list_text(count: int) -> str:
    return (
        "🔐 <b>Администраторы</b>\n\n"
        f"Всего администраторов: {count}\n\n"
        "Добавлять и удалять обычных администраторов может только суперадмин. "
        "Суперадмин защищён от удаления через бот."
    )


@router.callback_query(AdminMenuCB.filter(F.target == "admins"))
async def cb_list(callback: CallbackQuery, session: AsyncSession) -> None:
    admins = await crud.list_admins(session)
    await callback.message.edit_text(
        _list_text(len(admins)),
        reply_markup=admins_list_kb(admins, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ---------------------------- Добавление ---------------------------------

@router.callback_query(AdminManageCB.filter(F.action == "add"))
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminManageForm.entering_telegram_id)
    await callback.message.edit_text(
        "Введите Telegram ID нового администратора (число).\n\n"
        "Узнать свой ID пользователь может, например, у бота @userinfobot.",
        reply_markup=form_control_kb(),
    )
    await callback.answer()


@router.callback_query(StateFilter(AdminManageForm), FormControlCB.filter(F.action == "cancel"))
async def cb_form_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    current_state = await state.get_state()
    if current_state is None or not current_state.startswith("AdminManageForm"):
        return
    await state.clear()
    admins = await crud.list_admins(session)
    await callback.message.edit_text(
        _list_text(len(admins)), reply_markup=admins_list_kb(admins, callback.from_user.id), parse_mode="HTML"
    )
    await callback.answer("Отменено")


@router.message(AdminManageForm.entering_telegram_id, F.text)
async def add_telegram_id(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = message.text.strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("⚠️ Telegram ID должен быть числом. Попробуйте ещё раз.")
        return
    telegram_id = int(raw)

    if await crud.admin_exists(session, telegram_id):
        await state.clear()
        admins = await crud.list_admins(session)
        await message.answer(
            "Этот пользователь уже является администратором.",
            reply_markup=admins_list_kb(admins, message.from_user.id),
        )
        return

    await crud.add_admin(
        session,
        telegram_id=telegram_id,
        username=None,
        full_name=None,
        added_by=message.from_user.id,
    )
    await state.clear()
    admins = await crud.list_admins(session)
    await message.answer(
        f"✅ Администратор {telegram_id} добавлен.\n\n"
        "Обратите внимание: чтобы новый администратор увидел свои username/имя "
        "в списке, ему нужно написать боту хотя бы раз (/start).",
        reply_markup=admins_list_kb(admins, message.from_user.id),
    )


@router.message(AdminManageForm.entering_telegram_id)
async def add_telegram_id_wrong(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте числовой Telegram ID.")


# ---------------------------- Удаление ------------------------------------

@router.callback_query(AdminManageCB.filter(F.action == "delete_confirm"))
async def cb_delete_confirm(callback: CallbackQuery, callback_data: AdminManageCB, session: AsyncSession) -> None:
    admin = await crud.get_admin_by_id(session, callback_data.admin_id)
    if not admin:
        await callback.answer("Не найдено.", show_alert=True)
        return
    total = await crud.count_admins(session)
    if admin.is_superadmin:
        await callback.answer(
            "Суперадмина нельзя удалить через бот.",
            show_alert=True,
        )
        return
    if total <= 1:
        await callback.answer(
            "⚠️ Нельзя удалить последнего администратора — тогда никто не "
            "сможет попасть в админ-панель.",
            show_alert=True,
        )
        return
    label = f"{admin.telegram_id}" + (f" (@{admin.username})" if admin.username else "")
    await callback.message.edit_text(
        f"Удалить администратора {label}?",
        reply_markup=admin_delete_confirm_kb(admin.id),
    )
    await callback.answer()


@router.callback_query(AdminManageCB.filter(F.action == "delete_cancel"))
async def cb_delete_cancel(callback: CallbackQuery, session: AsyncSession) -> None:
    admins = await crud.list_admins(session)
    await callback.message.edit_text(
        _list_text(len(admins)), reply_markup=admins_list_kb(admins, callback.from_user.id), parse_mode="HTML"
    )
    await callback.answer("Отменено")


@router.callback_query(AdminManageCB.filter(F.action == "delete_do"))
async def cb_delete_do(callback: CallbackQuery, callback_data: AdminManageCB, session: AsyncSession) -> None:
    ok, reason = await crud.delete_admin(session, callback_data.admin_id)
    admins = await crud.list_admins(session)
    if ok:
        text = "🗑 Администратор удалён."
    elif reason == "last_admin":
        text = "⚠️ Нельзя удалить последнего администратора."
    elif reason == "superadmin":
        text = "⚠️ Суперадмина нельзя удалить через бот."
    else:
        text = "Не удалось удалить — администратор не найден."
    await callback.message.edit_text(
        f"{text}\n\n{_list_text(len(admins))}",
        reply_markup=admins_list_kb(admins, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()
