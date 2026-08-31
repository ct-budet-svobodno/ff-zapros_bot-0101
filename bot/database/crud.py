"""
Репозиторий: все обращения к БД собраны здесь, чтобы хендлеры не содержали
"сырых" SQLAlchemy-запросов и было проще поддерживать проект.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Admin,
    ContentSection,
    CouncilLeader,
    Digest,
    Document,
    FacultyAdminPerson,
    Request,
    RequestResponse,
    RequestResponseStatus,
    RequestStatus,
    StudentOrganization,
    User,
)


# --------------------------------------------------------------------------
# Пользователи / администраторы
# --------------------------------------------------------------------------

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        # Обновим username/имя на случай, если они изменились в Telegram.
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()
        return user
    user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        # Два апдейта одного Telegram-пользователя могут одновременно пройти
        # SELECT. Один INSERT победит; после rollback возвращаем эту запись.
        await session.rollback()
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            raise
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()
        return user


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    admin = await session.scalar(select(Admin).where(Admin.telegram_id == telegram_id))
    return admin is not None


async def get_admin_by_telegram_id(session: AsyncSession, telegram_id: int) -> Admin | None:
    return await session.scalar(select(Admin).where(Admin.telegram_id == telegram_id))


async def add_admin(
    session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None,
    added_by: int | None,
) -> Admin:
    admin = Admin(telegram_id=telegram_id, username=username, full_name=full_name, added_by=added_by)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def list_admins(session: AsyncSession) -> list[Admin]:
    result = await session.scalars(select(Admin).order_by(Admin.added_at))
    return list(result.all())


async def count_admins(session: AsyncSession) -> int:
    return await session.scalar(select(func.count(Admin.id))) or 0


async def get_admin_by_id(session: AsyncSession, admin_id: int) -> Admin | None:
    return await session.get(Admin, admin_id)


async def admin_exists(session: AsyncSession, telegram_id: int) -> bool:
    return await is_admin(session, telegram_id)


async def delete_admin(session: AsyncSession, admin_id: int) -> tuple[bool, str]:
    """
    Удаляет администратора, но никогда не позволяет удалить последнего.
    Возвращает (успех, код_причины): "ok" / "last_admin" / "not_found".
    """
    total = await count_admins(session)
    if total <= 1:
        return False, "last_admin"
    admin = await session.get(Admin, admin_id)
    if not admin:
        return False, "not_found"
    await session.delete(admin)
    await session.commit()
    return True, "ok"


# --------------------------------------------------------------------------
# Контентные секции (тексты)
# --------------------------------------------------------------------------

async def get_section(session: AsyncSession, key: str) -> ContentSection | None:
    return await session.scalar(select(ContentSection).where(ContentSection.key == key))


async def update_section_body(session: AsyncSession, key: str, new_body: str) -> ContentSection | None:
    section = await get_section(session, key)
    if section:
        section.body = new_body
        await session.commit()
        await session.refresh(section)
    return section


# --------------------------------------------------------------------------
# Администрация факультета
# --------------------------------------------------------------------------

async def list_faculty_admins(session: AsyncSession, only_active: bool = True) -> list[FacultyAdminPerson]:
    stmt = select(FacultyAdminPerson).order_by(FacultyAdminPerson.sort_order)
    if only_active:
        stmt = stmt.where(FacultyAdminPerson.is_active.is_(True))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_faculty_admin(session: AsyncSession, person_id: int) -> FacultyAdminPerson | None:
    return await session.get(FacultyAdminPerson, person_id)


async def add_faculty_admin(session: AsyncSession, **kwargs) -> FacultyAdminPerson:
    person = FacultyAdminPerson(**kwargs)
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return person


async def update_faculty_admin(session: AsyncSession, person_id: int, **kwargs) -> FacultyAdminPerson | None:
    person = await session.get(FacultyAdminPerson, person_id)
    if person:
        for key, value in kwargs.items():
            setattr(person, key, value)
        await session.commit()
        await session.refresh(person)
    return person


async def set_faculty_admin_active(session: AsyncSession, person_id: int, is_active: bool) -> FacultyAdminPerson | None:
    return await update_faculty_admin(session, person_id, is_active=is_active)


async def delete_faculty_admin(session: AsyncSession, person_id: int) -> bool:
    person = await session.get(FacultyAdminPerson, person_id)
    if not person:
        return False
    await session.delete(person)
    await session.commit()
    return True


# --------------------------------------------------------------------------
# Студенческие организации
# --------------------------------------------------------------------------

async def list_org_category_representatives(
    session: AsyncSession,
    only_active: bool = True,
) -> list[StudentOrganization]:
    """Вернуть по одной записи на категорию для компактных callback-кнопок.

    Название категории нельзя помещать в callback_data: Telegram ограничивает
    его 64 байтами, а русские названия быстро превышают этот лимит.
    """
    stmt = select(StudentOrganization).order_by(
        StudentOrganization.category,
        StudentOrganization.id,
    )
    if only_active:
        stmt = stmt.where(StudentOrganization.is_active.is_(True))
    result = await session.scalars(stmt)
    representatives: dict[str, StudentOrganization] = {}
    for organization in result.all():
        representatives.setdefault(organization.category, organization)
    return list(representatives.values())


async def list_organizations(
    session: AsyncSession, category: str | None = None, only_active: bool = True
) -> list[StudentOrganization]:
    stmt = select(StudentOrganization).order_by(StudentOrganization.sort_order)
    if category:
        stmt = stmt.where(StudentOrganization.category == category)
    if only_active:
        stmt = stmt.where(StudentOrganization.is_active.is_(True))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_organization(session: AsyncSession, org_id: int) -> StudentOrganization | None:
    return await session.get(StudentOrganization, org_id)


async def add_organization(session: AsyncSession, **kwargs) -> StudentOrganization:
    org = StudentOrganization(**kwargs)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


async def update_organization(session: AsyncSession, org_id: int, **kwargs) -> StudentOrganization | None:
    org = await session.get(StudentOrganization, org_id)
    if org:
        for key, value in kwargs.items():
            setattr(org, key, value)
        await session.commit()
        await session.refresh(org)
    return org


async def set_organization_active(session: AsyncSession, org_id: int, is_active: bool) -> StudentOrganization | None:
    return await update_organization(session, org_id, is_active=is_active)


async def delete_organization(session: AsyncSession, org_id: int) -> bool:
    org = await session.get(StudentOrganization, org_id)
    if not org:
        return False
    await session.delete(org)
    await session.commit()
    return True


# --------------------------------------------------------------------------
# Руководители Студсовета
# --------------------------------------------------------------------------

async def list_council_leaders(session: AsyncSession, only_active: bool = True) -> list[CouncilLeader]:
    stmt = select(CouncilLeader).order_by(CouncilLeader.sort_order)
    if only_active:
        stmt = stmt.where(CouncilLeader.is_active.is_(True))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_council_leader(session: AsyncSession, leader_id: int) -> CouncilLeader | None:
    return await session.get(CouncilLeader, leader_id)


async def add_council_leader(session: AsyncSession, **kwargs) -> CouncilLeader:
    leader = CouncilLeader(**kwargs)
    session.add(leader)
    await session.commit()
    await session.refresh(leader)
    return leader


async def update_council_leader(session: AsyncSession, leader_id: int, **kwargs) -> CouncilLeader | None:
    leader = await session.get(CouncilLeader, leader_id)
    if leader:
        for key, value in kwargs.items():
            setattr(leader, key, value)
        await session.commit()
        await session.refresh(leader)
    return leader


async def set_council_leader_active(session: AsyncSession, leader_id: int, is_active: bool) -> CouncilLeader | None:
    return await update_council_leader(session, leader_id, is_active=is_active)


async def delete_council_leader(session: AsyncSession, leader_id: int) -> bool:
    leader = await session.get(CouncilLeader, leader_id)
    if not leader:
        return False
    await session.delete(leader)
    await session.commit()
    return True


# --------------------------------------------------------------------------
# Дайджесты
# --------------------------------------------------------------------------

async def list_digests(session: AsyncSession, only_active: bool = True) -> list[Digest]:
    stmt = select(Digest).order_by(Digest.created_at.desc())
    if only_active:
        stmt = stmt.where(Digest.is_active.is_(True))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_digest(session: AsyncSession, digest_id: int) -> Digest | None:
    return await session.get(Digest, digest_id)


async def add_digest(session: AsyncSession, **kwargs) -> Digest:
    digest = Digest(**kwargs)
    session.add(digest)
    await session.commit()
    await session.refresh(digest)
    return digest


async def update_digest_text(session: AsyncSession, digest_id: int, new_text: str) -> Digest | None:
    digest = await session.get(Digest, digest_id)
    if digest:
        digest.text = new_text
        await session.commit()
        await session.refresh(digest)
    return digest


async def delete_digest(session: AsyncSession, digest_id: int) -> bool:
    digest = await session.get(Digest, digest_id)
    if not digest:
        return False
    await session.delete(digest)
    await session.commit()
    return True


# --------------------------------------------------------------------------
# Документы
# --------------------------------------------------------------------------

async def list_documents(session: AsyncSession, only_active: bool = True) -> list[Document]:
    stmt = select(Document).order_by(Document.sort_order)
    if only_active:
        stmt = stmt.where(Document.is_active.is_(True))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_document(session: AsyncSession, document_id: int) -> Document | None:
    return await session.get(Document, document_id)


async def add_document(session: AsyncSession, **kwargs) -> Document:
    document = Document(**kwargs)
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def update_document(session: AsyncSession, document_id: int, **kwargs) -> Document | None:
    document = await session.get(Document, document_id)
    if document:
        for key, value in kwargs.items():
            setattr(document, key, value)
        await session.commit()
        await session.refresh(document)
    return document


async def delete_document(session: AsyncSession, document_id: int) -> bool:
    document = await session.get(Document, document_id)
    if not document:
        return False
    await session.delete(document)
    await session.commit()
    return True


# --------------------------------------------------------------------------
# Обращения
# --------------------------------------------------------------------------

async def create_request(
    session: AsyncSession,
    user_id: int,
    is_anonymous: bool,
    course: str,
    building: str,
    question_text: str,
) -> Request:
    request = Request(
        user_id=user_id,
        is_anonymous=is_anonymous,
        course=course,
        building=building,
        question_text=question_text,
        status=RequestStatus.NEW.value,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def get_request(session: AsyncSession, request_id: int) -> Request | None:
    return await session.get(Request, request_id)


async def get_request_by_group_message(
    session: AsyncSession, chat_id: int, message_id: int
) -> Request | None:
    return await session.scalar(
        select(Request).where(
            Request.group_chat_id == chat_id,
            Request.group_message_id == message_id,
        )
    )


async def set_request_group_message(
    session: AsyncSession, request_id: int, chat_id: int, message_id: int
) -> None:
    request = await session.get(Request, request_id)
    if request:
        request.group_chat_id = chat_id
        request.group_message_id = message_id
        await session.commit()


async def create_response_draft(
    session: AsyncSession,
    request_id: int,
    admin_id: int,
    text: str,
    source_message_id: int,
) -> RequestResponse:
    response = RequestResponse(
        request_id=request_id,
        admin_id=admin_id,
        text=text,
        source_message_id=source_message_id,
        status=RequestResponseStatus.DRAFT.value,
    )
    session.add(response)
    await session.commit()
    await session.refresh(response)
    return response


async def get_response(session: AsyncSession, response_id: int) -> RequestResponse | None:
    return await session.get(RequestResponse, response_id)


async def set_response_preview_message(
    session: AsyncSession, response_id: int, message_id: int
) -> None:
    response = await session.get(RequestResponse, response_id)
    if response:
        response.preview_message_id = message_id
        await session.commit()


async def claim_response_for_sending(
    session: AsyncSession, response_id: int, admin_id: int
) -> RequestResponse | None:
    stmt = (
        update(RequestResponse)
        .where(
            RequestResponse.id == response_id,
            RequestResponse.admin_id == admin_id,
            RequestResponse.status.in_([
                RequestResponseStatus.DRAFT.value,
                RequestResponseStatus.FAILED.value,
            ]),
        )
        .values(status=RequestResponseStatus.SENDING.value)
    )
    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount != 1:
        return None
    return await session.get(RequestResponse, response_id, populate_existing=True)


async def mark_response_failed(session: AsyncSession, response_id: int) -> RequestResponse | None:
    response = await session.get(RequestResponse, response_id)
    if response:
        response.status = RequestResponseStatus.FAILED.value
        await session.commit()
        await session.refresh(response)
    return response


async def mark_response_sent(session: AsyncSession, response_id: int) -> RequestResponse | None:
    response = await session.get(RequestResponse, response_id)
    if response is None:
        return None

    response.status = RequestResponseStatus.SENT.value
    response.sent_at = datetime.utcnow()

    request = await session.get(Request, response.request_id)
    if request:
        # Поле сохраняется для обратной совместимости; полная история живёт
        # в request_responses.
        request.response_text = response.text
        if request.status == RequestStatus.NEW.value:
            request.status = RequestStatus.IN_PROGRESS.value
            request.taken_at = datetime.utcnow()
        if request.admin_id is None:
            request.admin_id = response.admin_id

    await session.commit()
    await session.refresh(response)
    return response


async def cancel_response(
    session: AsyncSession, response_id: int, admin_id: int
) -> RequestResponse | None:
    response = await session.get(RequestResponse, response_id)
    if (
        response is None
        or response.admin_id != admin_id
        or response.status not in {
            RequestResponseStatus.DRAFT.value,
            RequestResponseStatus.FAILED.value,
        }
    ):
        return None
    response.status = RequestResponseStatus.CANCELLED.value
    await session.commit()
    await session.refresh(response)
    return response


async def count_sent_responses(session: AsyncSession, request_id: int) -> int:
    return await session.scalar(
        select(func.count(RequestResponse.id)).where(
            RequestResponse.request_id == request_id,
            RequestResponse.status == RequestResponseStatus.SENT.value,
        )
    ) or 0


async def close_request(session: AsyncSession, request_id: int) -> Request | None:
    result = await session.execute(
        update(Request)
        .where(
            Request.id == request_id,
            Request.status != RequestStatus.CLOSED.value,
        )
        .values(
            status=RequestStatus.CLOSED.value,
            closed_at=datetime.utcnow(),
        )
    )
    await session.commit()
    if result.rowcount != 1:
        return None
    return await session.get(Request, request_id, populate_existing=True)


async def get_requests_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(Request.id))) or 0
    new_count = await session.scalar(
        select(func.count(Request.id)).where(Request.status == RequestStatus.NEW.value)
    ) or 0
    in_progress = await session.scalar(
        select(func.count(Request.id)).where(Request.status == RequestStatus.IN_PROGRESS.value)
    ) or 0
    closed = await session.scalar(
        select(func.count(Request.id)).where(Request.status == RequestStatus.CLOSED.value)
    ) or 0
    anonymous = await session.scalar(
        select(func.count(Request.id)).where(Request.is_anonymous.is_(True))
    ) or 0
    return {
        "total": total,
        "new": new_count,
        "in_progress": in_progress,
        "closed": closed,
        "anonymous": anonymous,
        "non_anonymous": total - anonymous,
    }
