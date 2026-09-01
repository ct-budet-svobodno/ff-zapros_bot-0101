"""
Вспомогательные функции форматирования текста сообщений.
"""
from datetime import datetime

from database.models import Request, RequestStatus

STATUS_LABELS = {
    RequestStatus.NEW.value: "🆕 Новое",
    RequestStatus.IN_PROGRESS.value: "🔄 В работе",
    RequestStatus.CLOSED.value: "✅ Закрыто",
}


def fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "-"
    return dt.strftime("%d.%m.%Y %H:%M")


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def leader_position_button_text(position: str) -> str:
    """Короткая должность для кнопки списка руководителей."""
    normalized = position.casefold().replace("ё", "е")
    if "перв" in normalized and "замест" in normalized:
        return "Первый заместитель"
    if "проектн" in normalized and ("зам" in normalized or "замест" in normalized):
        return "Зам по проектной деятельности"
    if (
        ("учебно-социальн" in normalized or "уч-соц" in normalized)
        and ("зам" in normalized or "замест" in normalized)
    ):
        return "Зам по уч-соц деятельности"
    if ("внешн" in normalized and "связ" in normalized) or "нвс" in normalized:
        return "Руководитель НВС"
    if "информационн" in normalized and "направлен" in normalized:
        return "Руководитель информа"
    if (
        ("развит" in normalized and "корпоративн" in normalized)
        or "нркк" in normalized
    ):
        return "Руководитель НРКК"
    return position


def leader_position_detail_text(position: str) -> str:
    """Полная расшифровка сокращённых направлений в карточке."""
    normalized = position.casefold().replace("ё", "е")
    if ("внешн" in normalized and "связ" in normalized) or "нвс" in normalized:
        return "Руководитель направления внешних связей (НВС)"
    if "информационн" in normalized or "руководитель информа" in normalized:
        return "Руководитель информационного направления"
    if (
        ("развит" in normalized and "корпоративн" in normalized)
        or "нркк" in normalized
    ):
        return (
            "Руководитель направления развития и корпоративной культуры "
            "(НРКК)"
        )
    return leader_position_button_text(position)


def request_preview_text(is_anonymous: bool, course: str, building: str, question: str) -> str:
    anon_label = "🕶 Анонимно" if is_anonymous else "👤 Не анонимно"
    return (
        "📨 Проверьте ваше обращение:\n\n"
        f"Анонимность: {anon_label}\n"
        f"Курс: {course}\n"
        f"Корпус: {building}\n\n"
        f"Вопрос:\n{escape_html(question)}"
    )


def group_message_text(request: Request, author_label: str, response_count: int = 0) -> str:
    status_label = STATUS_LABELS.get(request.status, request.status)
    header = f"📨 НОВОЕ ОБРАЩЕНИЕ #{request.id}" if request.status == RequestStatus.NEW.value \
        else f"📨 ОБРАЩЕНИЕ #{request.id}"
    lines = [
        header,
        "",
        author_label,
        f"🎓 Курс: {request.course}",
        f"🏢 Корпус: {request.building}",
        "",
        "Вопрос:",
        escape_html(request.question_text),
        "",
        f"🕐 {fmt_dt(request.created_at)}",
        "",
        f"Статус: {status_label}",
        f"💬 Ответов доставлено: {response_count}",
    ]
    if request.status != RequestStatus.CLOSED.value:
        lines.extend([
            "",
            "↩️ Чтобы ответить, используйте Reply на это сообщение.",
        ])
    return "\n".join(lines)


def author_label(request: Request, username: str | None, full_name: str | None) -> str:
    if request.is_anonymous:
        return "🕶 Анонимное обращение"
    if username:
        return f"👤 @{escape_html(username)}"
    return f"👤 {escape_html(full_name or 'Без имени')}"
