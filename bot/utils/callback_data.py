"""
CallbackData-фабрики (aiogram 3 filters.callback_data). Использование
типизированных фабрик вместо ручных строк снижает риск ошибок в парсинге.
"""
from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    target: str  # about, council, docs, ask, back, home, admins, orgs...


class OrgCategoryCB(CallbackData, prefix="orgcat"):
    category: str


class OrgItemCB(CallbackData, prefix="org"):
    org_id: int


class DocItemCB(CallbackData, prefix="doc"):
    doc_id: int


class DigestItemCB(CallbackData, prefix="digest"):
    digest_id: int


class AnonymityCB(CallbackData, prefix="anon"):
    value: str  # "yes" / "no"


class CourseCB(CallbackData, prefix="course"):
    value: str


class BuildingCB(CallbackData, prefix="building"):
    value: str


class RequestPreviewCB(CallbackData, prefix="reqprev"):
    action: str  # send / edit / cancel


class RequestActionCB(CallbackData, prefix="req"):
    action: str  # take / reply / close
    request_id: int


class ResponsePreviewCB(CallbackData, prefix="respprev"):
    action: str  # send / cancel
    request_id: int


# ---------------------- Админка: контент --------------------------------

class AdminMenuCB(CallbackData, prefix="adm"):
    target: str


class SectionCB(CallbackData, prefix="sect"):
    key: str
    action: str  # view / edit


class SectionPreviewCB(CallbackData, prefix="sectprev"):
    key: str
    action: str  # save / cancel


class FacultyAdminCB(CallbackData, prefix="fadm"):
    action: str  # list / admview / view / add / delete / edit_menu / edit_field / toggle_active / delete_photo
    person_id: int = 0
    field: str = ""  # name / position / contact / photo


class OrgAdminCB(CallbackData, prefix="orgadm"):
    action: str  # list / view / add / delete / choose_cat / edit_menu / edit_field / toggle_active
    org_id: int = 0
    category: str = ""
    field: str = ""  # category / name / description / link


class LeaderAdminCB(CallbackData, prefix="ladm"):
    action: str  # list / admview / view / add / delete / edit_menu / edit_field / toggle_active / delete_photo
    leader_id: int = 0
    field: str = ""  # name / position / username / photo


class DigestAdminCB(CallbackData, prefix="dgadm"):
    action: str  # list / view / add / edit / delete
    digest_id: int = 0


class DocAdminCB(CallbackData, prefix="docadm"):
    action: str  # list / view / add / edit_title / edit_desc / edit_file / delete
    doc_id: int = 0


class FormControlCB(CallbackData, prefix="form"):
    action: str  # save / cancel / skip


class AdminManageCB(CallbackData, prefix="adminmgt"):
    action: str  # list / add / delete_confirm / delete_do / delete_cancel
    admin_id: int = 0
