from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import CouncilLeader, Digest, Document, FacultyAdminPerson, StudentOrganization
from keyboards.common_kb import kb_with_nav, short_button_text
from utils.callback_data import (
    AnonymityCB,
    BuildingCB,
    CourseCB,
    DigestItemCB,
    DocItemCB,
    FacultyAdminCB,
    LeaderAdminCB,
    MenuCB,
    OrgCategoryCB,
    OrgItemCB,
    RequestPreviewCB,
)
from utils.formatting import leader_position_button_text


def about_faculty_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="👥 Администрация", callback_data=MenuCB(target="faculty_admins").pack())],
        [InlineKeyboardButton(text="🤝 Студенческие организации", callback_data=MenuCB(target="orgs").pack())],
    ]
    return kb_with_nav(rows, back_target="home")


def faculty_admins_kb(people: list[FacultyAdminPerson]) -> InlineKeyboardMarkup:
    rows = []
    if not people:
        return kb_with_nav([], back_target="about")
    for p in people:
        rows.append([InlineKeyboardButton(
            text=short_button_text(p.full_name), callback_data=FacultyAdminCB(action="view", person_id=p.id).pack()
        )])
    return kb_with_nav(rows, back_target="about")


def org_categories_kb(categories: list[StudentOrganization]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=short_button_text(org.category),
        callback_data=OrgCategoryCB(org_id=org.id).pack(),
    )] for org in categories]
    return kb_with_nav(rows, back_target="about")


def org_items_kb(items: list[StudentOrganization]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(i.name), callback_data=OrgItemCB(org_id=i.id).pack())] for i in items]
    return kb_with_nav(rows, back_target="orgs")


def org_item_detail_kb(org: StudentOrganization) -> InlineKeyboardMarkup:
    rows = []
    if org.link and org.link.startswith(("http://", "https://")):
        rows.append([InlineKeyboardButton(text="🔗 Открыть ссылку", url=org.link)])
    rows.append([InlineKeyboardButton(
        text="⬅️ Назад", callback_data=OrgCategoryCB(org_id=org.id).pack()
    )])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCB(target="home_inline").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def council_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="👥 Руководители", callback_data=MenuCB(target="leaders").pack())],
        [InlineKeyboardButton(text="📅 Дайджест мероприятий", callback_data=MenuCB(target="digests").pack())],
        [InlineKeyboardButton(text="📝 Отбор в Студенческий совет", callback_data=MenuCB(target="selection").pack())],
        [InlineKeyboardButton(text="📱 Медиа", callback_data=MenuCB(target="media").pack())],
    ]
    return kb_with_nav(rows, back_target="home")


def leaders_kb(leaders: list[CouncilLeader]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=short_button_text(leader_position_button_text(l.position)),
        callback_data=LeaderAdminCB(action="view", leader_id=l.id).pack(),
    )] for l in leaders]
    return kb_with_nav(rows, back_target="council")


def digests_kb(digests: list[Digest]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(d.month_label), callback_data=DigestItemCB(digest_id=d.id).pack())]
            for d in digests]
    return kb_with_nav(rows, back_target="council")


def media_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Открытая группа Студсовета", url="https://t.me/sst_finfak")],
        [InlineKeyboardButton(text="StudAc (Telegram)", url="https://t.me/stud_ac")],
        [InlineKeyboardButton(text="StudAc (VK)", url="https://vk.ru/stud_ac")],
        [InlineKeyboardButton(text="Канал Финансового факультета", url="https://t.me/ff_finuniver")],
    ]
    return kb_with_nav(rows, back_target="council")


def documentation_kb(documents: list[Document]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=short_button_text(f"📄 {d.title}"), callback_data=DocItemCB(doc_id=d.id).pack())]
            for d in documents]
    return kb_with_nav(rows, back_target="home")


def anonymity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🕶 Анонимно", callback_data=AnonymityCB(value="yes").pack()),
                InlineKeyboardButton(text="👤 Не анонимно", callback_data=AnonymityCB(value="no").pack()),
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="reqcancel")],
        ]
    )


def course_kb() -> InlineKeyboardMarkup:
    options = ["1 курс", "2 курс", "3 курс", "4 курс", "Магистратура"]
    rows = [[InlineKeyboardButton(text=o, callback_data=CourseCB(value=o).pack())] for o in options]
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data="reqcancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def building_kb() -> InlineKeyboardMarkup:
    options = ["Китай-город", "Фили"]
    rows = [[InlineKeyboardButton(text=f"🏢 {o}", callback_data=BuildingCB(value=o).pack())] for o in options]
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data="reqcancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def request_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data=RequestPreviewCB(action="send").pack())],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=RequestPreviewCB(action="edit").pack())],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=RequestPreviewCB(action="cancel").pack())],
        ]
    )
