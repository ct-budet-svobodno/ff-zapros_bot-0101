from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import (
    ContentSection,
    CouncilLeader,
    Digest,
    Document,
    FacultyAdminPerson,
    StudentOrganization,
)
from keyboards.common_kb import short_button_text
from utils.callback_data import (
    AdminManageCB,
    AdminMenuCB,
    DigestAdminCB,
    DocAdminCB,
    FacultyAdminCB,
    FormControlCB,
    LeaderAdminCB,
    OrgAdminCB,
    RequestActionCB,
    ResponseActionCB,
    SectionCB,
    SectionPreviewCB,
)


def admin_main_menu_kb(is_superadmin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📝 Управление информацией", callback_data=AdminMenuCB(target="content").pack())],
        [InlineKeyboardButton(text="📚 Управление документацией", callback_data=AdminMenuCB(target="docs").pack())],
        [InlineKeyboardButton(text="📨 Обращения студентов", callback_data=AdminMenuCB(target="requests").pack())],
        [InlineKeyboardButton(text="📅 Дайджест мероприятий", callback_data=AdminMenuCB(target="digests").pack())],
        [InlineKeyboardButton(text="👥 Руководители Студсовета", callback_data=AdminMenuCB(target="leaders").pack())],
    ]
    if is_superadmin:
        rows.append([
            InlineKeyboardButton(
                text="🔐 Администраторы",
                callback_data=AdminMenuCB(target="admins").pack(),
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_back_kb(target: str = "root") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target=target).pack())]]
    )


def content_management_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📖 Тексты (история, инфо о Студсовете, отбор)",
                               callback_data=AdminMenuCB(target="content_sections").pack())],
        [InlineKeyboardButton(text="👥 Руководство факультета", callback_data=AdminMenuCB(target="content_fadmins").pack())],
        [InlineKeyboardButton(text="🤝 Студенческие организации", callback_data=AdminMenuCB(target="content_orgs").pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sections_list_kb(sections: list[ContentSection]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(s.title), callback_data=SectionCB(key=s.key, action="view").pack())]
            for s in sections]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="content").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def section_detail_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=SectionCB(key=key, action="edit").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="content_sections").pack())],
        ]
    )


def section_preview_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=SectionPreviewCB(key=key, action="save").pack())],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=SectionPreviewCB(key=key, action="cancel").pack())],
        ]
    )


def fadmins_list_kb(people: list[FacultyAdminPerson]) -> InlineKeyboardMarkup:
    rows = []
    for p in people:
        label = p.full_name if p.is_active else f"🚫 {p.full_name}"
        rows.append([InlineKeyboardButton(
            text=short_button_text(label), callback_data=FacultyAdminCB(action="admview", person_id=p.id).pack()
        )])
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data=FacultyAdminCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="content").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fadmin_detail_kb(person: FacultyAdminPerson) -> InlineKeyboardMarkup:
    visibility_text = "🚫 Скрыть от пользователей" if person.is_active else "👁 Показывать пользователям"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=FacultyAdminCB(action="edit_menu", person_id=person.id).pack())],
            [InlineKeyboardButton(text=visibility_text, callback_data=FacultyAdminCB(action="toggle_active", person_id=person.id).pack())],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=FacultyAdminCB(action="delete", person_id=person.id).pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=FacultyAdminCB(action="list").pack())],
        ]
    )


def fadmin_edit_menu_kb(person: FacultyAdminPerson) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="ФИО", callback_data=FacultyAdminCB(action="edit_field", person_id=person.id, field="full_name").pack())],
        [InlineKeyboardButton(text="Должность", callback_data=FacultyAdminCB(action="edit_field", person_id=person.id, field="position").pack())],
        [InlineKeyboardButton(text="Контакты", callback_data=FacultyAdminCB(action="edit_field", person_id=person.id, field="contact_info").pack())],
        [InlineKeyboardButton(text="🖼 Заменить фото", callback_data=FacultyAdminCB(action="edit_field", person_id=person.id, field="photo").pack())],
    ]
    if person.photo_file_id:
        rows.append([InlineKeyboardButton(text="🗑 Удалить фото", callback_data=FacultyAdminCB(action="delete_photo", person_id=person.id).pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=FacultyAdminCB(action="admview", person_id=person.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def form_control_kb(include_skip: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if include_skip:
        rows.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data=FormControlCB(action="skip").pack())])
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data=FormControlCB(action="cancel").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def form_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=FormControlCB(action="save").pack())],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=FormControlCB(action="cancel").pack())],
        ]
    )


def orgs_categories_admin_kb(
    categories: list[StudentOrganization],
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=short_button_text(org.category),
        callback_data=OrgAdminCB(action="choose_cat", org_id=org.id).pack(),
    )] for org in categories]
    rows.append([InlineKeyboardButton(text="➕ Добавить организацию", callback_data=OrgAdminCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="content").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orgs_list_admin_kb(orgs: list[StudentOrganization]) -> InlineKeyboardMarkup:
    rows = []
    for o in orgs:
        label = o.name if o.is_active else f"🚫 {o.name}"
        rows.append([InlineKeyboardButton(
            text=short_button_text(label), callback_data=OrgAdminCB(action="view", org_id=o.id).pack()
        )])
    if orgs:
        rows.append([InlineKeyboardButton(
            text="➕ Добавить в эту категорию",
            callback_data=OrgAdminCB(action="add", org_id=orgs[0].id).pack(),
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="content_orgs").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def org_detail_admin_kb(org: StudentOrganization) -> InlineKeyboardMarkup:
    visibility_text = "🚫 Скрыть от пользователей" if org.is_active else "👁 Показывать пользователям"
    text_action = "📝 Изменить текст" if org.description else "➕ Добавить текст"
    rows = [
        [InlineKeyboardButton(
            text=text_action,
            callback_data=OrgAdminCB(
                action="edit_field",
                org_id=org.id,
                field="description",
            ).pack(),
        )],
    ]
    if org.description:
        rows.append([InlineKeyboardButton(
            text="🧹 Удалить текст",
            callback_data=OrgAdminCB(action="clear_text", org_id=org.id).pack(),
        )])
    rows.extend([
        [InlineKeyboardButton(text="⚙️ Название, категория и ссылка", callback_data=OrgAdminCB(action="edit_menu", org_id=org.id).pack())],
        [InlineKeyboardButton(text=visibility_text, callback_data=OrgAdminCB(action="toggle_active", org_id=org.id).pack())],
        [InlineKeyboardButton(text="🗑 Удалить организацию целиком", callback_data=OrgAdminCB(action="delete", org_id=org.id).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=OrgAdminCB(action="choose_cat", org_id=org.id).pack())],
    ])
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def org_clear_text_confirm_kb(org_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Да, удалить только текст",
                callback_data=OrgAdminCB(action="clear_text_confirm", org_id=org_id).pack(),
            )],
            [InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=OrgAdminCB(action="view", org_id=org_id).pack(),
            )],
        ]
    )


def org_edit_menu_kb(org: StudentOrganization) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Категория", callback_data=OrgAdminCB(action="edit_field", org_id=org.id, field="category").pack())],
        [InlineKeyboardButton(text="Название", callback_data=OrgAdminCB(action="edit_field", org_id=org.id, field="name").pack())],
        [InlineKeyboardButton(text="Ссылка", callback_data=OrgAdminCB(action="edit_field", org_id=org.id, field="link").pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=OrgAdminCB(action="view", org_id=org.id).pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def leaders_list_admin_kb(leaders: list[CouncilLeader]) -> InlineKeyboardMarkup:
    rows = []
    for l in leaders:
        label = l.full_name if l.is_active else f"🚫 {l.full_name}"
        rows.append([InlineKeyboardButton(
            text=short_button_text(label), callback_data=LeaderAdminCB(action="admview", leader_id=l.id).pack()
        )])
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data=LeaderAdminCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def leader_detail_admin_kb(leader: CouncilLeader) -> InlineKeyboardMarkup:
    visibility_text = "🚫 Скрыть от пользователей" if leader.is_active else "👁 Показывать пользователям"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=LeaderAdminCB(action="edit_menu", leader_id=leader.id).pack())],
            [InlineKeyboardButton(text=visibility_text, callback_data=LeaderAdminCB(action="toggle_active", leader_id=leader.id).pack())],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=LeaderAdminCB(action="delete", leader_id=leader.id).pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=LeaderAdminCB(action="list").pack())],
        ]
    )


def leader_edit_menu_kb(leader: CouncilLeader) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="ФИО", callback_data=LeaderAdminCB(action="edit_field", leader_id=leader.id, field="full_name").pack())],
        [InlineKeyboardButton(text="Должность", callback_data=LeaderAdminCB(action="edit_field", leader_id=leader.id, field="position").pack())],
        [InlineKeyboardButton(text="Telegram username", callback_data=LeaderAdminCB(action="edit_field", leader_id=leader.id, field="telegram_username").pack())],
        [InlineKeyboardButton(text="🖼 Заменить фото", callback_data=LeaderAdminCB(action="edit_field", leader_id=leader.id, field="photo").pack())],
    ]
    if leader.photo_file_id:
        rows.append([InlineKeyboardButton(text="🗑 Удалить фото", callback_data=LeaderAdminCB(action="delete_photo", leader_id=leader.id).pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=LeaderAdminCB(action="admview", leader_id=leader.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def digests_list_admin_kb(digests: list[Digest]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(d.month_label), callback_data=DigestAdminCB(action="view", digest_id=d.id).pack())]
            for d in digests]
    rows.append([InlineKeyboardButton(text="➕ Создать дайджест", callback_data=DigestAdminCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def digest_detail_admin_kb(digest_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=DigestAdminCB(action="edit", digest_id=digest_id).pack())],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=DigestAdminCB(action="delete", digest_id=digest_id).pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=DigestAdminCB(action="list").pack())],
        ]
    )


def docs_list_admin_kb(documents: list[Document]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(d.title), callback_data=DocAdminCB(action="view", doc_id=d.id).pack())]
            for d in documents]
    rows.append([InlineKeyboardButton(text="➕ Добавить документ", callback_data=DocAdminCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def doc_detail_admin_kb(doc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=DocAdminCB(action="edit_title", doc_id=doc_id).pack()),
             InlineKeyboardButton(text="✏️ Описание", callback_data=DocAdminCB(action="edit_desc", doc_id=doc_id).pack())],
            [InlineKeyboardButton(text="🔄 Заменить PDF", callback_data=DocAdminCB(action="edit_file", doc_id=doc_id).pack())],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=DocAdminCB(action="delete", doc_id=doc_id).pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=DocAdminCB(action="list").pack())],
        ]
    )


def request_group_kb(request_id: int, status: str) -> InlineKeyboardMarkup:
    from database.models import RequestStatus
    if status == RequestStatus.NEW.value:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="↩️ Как ответить", callback_data=RequestActionCB(action="reply", request_id=request_id).pack()
            )]]
        )
    if status == RequestStatus.IN_PROGRESS.value:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Как ответить", callback_data=RequestActionCB(action="reply", request_id=request_id).pack())],
                [InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=RequestActionCB(action="close", request_id=request_id).pack())],
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=[])


def response_preview_kb(response_id: int, retry: bool = False) -> InlineKeyboardMarkup:
    send_text = "🔄 Повторить отправку" if retry else "✅ Отправить студенту"
    action = "retry" if retry else "send"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=send_text,
                callback_data=ResponseActionCB(action=action, response_id=response_id).pack(),
            )],
            [InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=ResponseActionCB(action="cancel", response_id=response_id).pack(),
            )],
        ]
    )


def requests_menu_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика обращений", callback_data=AdminMenuCB(target="requests_stats").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())],
        ]
    )


# ---------------------- Управление администраторами ------------------------

def admins_list_kb(admins: list, current_telegram_id: int) -> InlineKeyboardMarkup:
    rows = []
    for a in admins:
        label = f"{a.telegram_id}"
        if a.username:
            label += f" (@{a.username})"
        if a.is_superadmin:
            label += " — суперадмин"
        if a.telegram_id == current_telegram_id:
            label += " — вы"
        row = [InlineKeyboardButton(text=label, callback_data="noop")]
        if not a.is_superadmin:
            row.append(
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=AdminManageCB(
                        action="delete_confirm",
                        admin_id=a.id,
                    ).pack(),
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(text="➕ Добавить администратора", callback_data=AdminManageCB(action="add").pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminMenuCB(target="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_delete_confirm_kb(admin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=AdminManageCB(action="delete_do", admin_id=admin_id).pack()),
                InlineKeyboardButton(text="❌ Отмена", callback_data=AdminManageCB(action="delete_cancel").pack()),
            ]
        ]
    )
