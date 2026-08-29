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


def request_preview_text(is_anonymous: bool, course: str, building: str, question: str) -> str:
    anon_label = "🕶 Анонимно" if is_anonymous else "👤 Не анонимно"
    return (
        "📨 Проверьте ваше обращение:\n\n"
        f"Анонимность: {anon_label}\n"
        f"Курс: {course}\n"
        f"Корпус: {building}\n\n"
        f"Вопрос:\n{escape_html(question)}"
    )


def group_message_text(request: Request, author_label: str) -> str:
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
    ]
    if request.admin_id and request.status != RequestStatus.NEW.value:
        lines.append(f"Ответственный: admin_id={request.admin_id}")
    return "\n".join(lines)


def author_label(request: Request, username: str | None, full_name: str | None) -> str:
    if request.is_anonymous:
        return "🕶 Анонимное обращение"
    if username:
        return f"👤 @{username}"
    return f"👤 {full_name or 'Без имени'}"
