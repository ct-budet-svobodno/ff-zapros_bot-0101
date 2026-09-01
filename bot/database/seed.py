"""
Первичное заполнение БД:
  * суперадминистраторы и начальные администраторы из .env;
  * тексты, зафиксированные в ТЗ (история факультета, инфо о Студсовете,
    текст об отборе);
  * руководители Студсовета (текущий состав из ТЗ, без фото — фото
    администратор добавит позже через админ-панель);
  * заготовки разделов студенческих организаций (без выдуманного контента —
    только то, что прямо указано в ТЗ; остальное — понятные placeholder'ы).

Скрипт идемпотентен: повторный запуск не создаёт дубликаты.
"""
import asyncio
import logging

from sqlalchemy import select, update

from config import settings
from database.engine import async_session_maker, init_db
from database.models import (
    Admin,
    ContentSection,
    CouncilLeader,
    OrgCategory,
    Request,
    RequestResponse,
    RequestResponseStatus,
    StudentOrganization,
)

logger = logging.getLogger(__name__)

FACULTY_HISTORY = (
    "Финансовый факультет ведет свою историю с 1919 года, когда был создан "
    "Московский финансово-экономический институт (МФЭИ).\n\n"
    "В 1921 году сформирован Финансовый факультет. За свою историю он "
    "несколько раз был реорганизован: в 1946 году вошел в состав Московского "
    "финансового института, в 1991 году стал Институтом финансов "
    "Государственной финансовой академии, в 2013 году был объединен с "
    "финансовыми факультетами присоединенных вузов, а в 2020 году приобрел "
    "современную структуру в результате объединения трех факультетов.\n\n"
    "Сегодня на факультете обучаются более 2500 студентов, которые получают "
    "образование в сфере финансов, банковского дела, страхования, финансовых "
    "рынков и финансового контроля."
)

COUNCIL_INFO = (
    "Студенческий совет Финансового факультета — подразделение Студенческого "
    "совета Финансового университета, целью работы которого является "
    "обеспечение учёта мнения обучающихся, закрытие запросов и потребностей "
    "студентов, а также организация их досуга.\n\n"
    "Работа нашего подразделения основывается на 5 видах деятельности, "
    "которые курируются Председателем, его Первым заместителем и Секретарем: "
    "Проектная деятельность, Учебно-Социальная деятельность, Информационное "
    "Направление, Направление Внешних Связей и Направление Развития и "
    "Корпоративной Культуры.\n\n"
    "Подробнее с работой каждого направления можно в Открытой группе "
    "Студенческого совета Финансового факультета: https://t.me/sst_finfak\n\n"
    "Ищи нас в 112 аудитории."
)

SELECTION_INFO = (
    "Информация о сроках и этапах отбора публикуется в Открытой группе "
    "Студенческого совета Финансового факультета дважды в год — в начале "
    "осени и зимы.\n\n"
    "Следи за обновлениями по ссылке: https://t.me/sst_finfak\n\n"
    "или в медиа нашего факультета: https://t.me/stud_ac"
)

CONTENT_SECTIONS = [
    ("faculty_history", "История факультета", FACULTY_HISTORY),
    ("council_info", "О Студенческом совете", COUNCIL_INFO),
    ("council_selection", "Отбор в Студенческий совет", SELECTION_INFO),
]

COUNCIL_LEADERS = [
    ("Шишкова Алина", "Председатель", "yourfloret", 0),
    ("Летуновская Екатерина", "Первый заместитель", "katrina007_0", 1),
    ("Беляева Анастасия", "Секретарь", "atnnasy", 2),
    ("Мазур Елизавета", "Зам по проектной деятельности", "dwimddd", 3),
    ("Андреев Сергей", "Зам по уч-соц деятельности", "foxssert", 4),
    ("Ефимов Мирон", "Руководитель направления внешних связей (НВС)", "mironefimov", 5),
    ("Дорохина Варвара", "Руководитель информационного направления", "ghtbrn", 6),
    ("Семенов Дмитрий", "Руководитель направления развития и корпоративной культуры (НРКК)", "preciouslittlediamondd", 7),
]

LEGACY_COUNCIL_LEADER_POSITIONS = {
    "yourfloret": "Председатель",
    "katrina007_0": "Первый Заместитель Председателя",
    "atnnasy": "Секретарь",
    "dwimddd": "Заместитель председателя по Проектной деятельности",
    "foxssert": "Заместитель председателя по Учебно-Социальной деятельности",
    "mironefimov": "Руководитель Направления Внешних Связей",
    "ghtbrn": "Руководитель Информационного Направления",
    "preciouslittlediamondd": (
        "Руководитель Направления Развития и Корпоративной Культуры"
    ),
}

# Комитеты прямо перечислены в ТЗ (расшифровку названий и описание
# заказчик предоставит позже — контент не придумываем).
COMMITTEES = ["КВС", "УСК", "ИК", "ПК"]

# Организации, чьё существование в ТЗ помечено как "требует подтверждения" —
# создаём как неактивные заготовки (is_active=False), чтобы админ мог
# включить/заполнить их позже, когда информация подтвердится.
PENDING_CLUBS = ["Клуб молодого финансиста", "Предпринимательский клуб"]


async def seed_admins(session) -> None:
    superadmin_ids = set(settings.superadmin_ids)
    bootstrap_ids = set(settings.initial_admin_ids) | superadmin_ids
    for admin_id in bootstrap_ids:
        existing = await session.scalar(select(Admin).where(Admin.telegram_id == admin_id))
        if not existing:
            session.add(
                Admin(
                    telegram_id=admin_id,
                    is_superadmin=admin_id in superadmin_ids,
                    added_by=None,
                )
            )
            logger.info("Добавлен начальный администратор: %s", admin_id)
        elif admin_id in superadmin_ids:
            existing.is_superadmin = True

    await session.flush()
    if superadmin_ids:
        all_admins = list(await session.scalars(select(Admin)))
        for admin in all_admins:
            admin.is_superadmin = admin.telegram_id in superadmin_ids

    has_superadmin = await session.scalar(
        select(Admin.id).where(Admin.is_superadmin.is_(True)).limit(1)
    )
    if has_superadmin is None:
        # Старые установки могут не иметь SUPERADMIN_ID в .env. Чтобы после
        # миграции не заблокировать управление, повышаем самого первого админа.
        first_admin = await session.scalar(select(Admin).order_by(Admin.added_at, Admin.id))
        if first_admin is not None:
            first_admin.is_superadmin = True
            logger.info(
                "Первый существующий администратор назначен суперадмином: %s",
                first_admin.telegram_id,
            )


async def seed_content_sections(session) -> None:
    for key, title, body in CONTENT_SECTIONS:
        existing = await session.scalar(select(ContentSection).where(ContentSection.key == key))
        if not existing:
            session.add(ContentSection(key=key, title=title, body=body))


async def seed_council_leaders(session) -> None:
    existing_leaders = list(await session.scalars(select(CouncilLeader)))
    if existing_leaders:
        # Порядок хранится в БД, поэтому обновляем его и для уже запущенных
        # установок. Старые стандартные названия должностей также заменяем,
        # но введённый администратором произвольный текст не трогаем.
        order_by_username = {
            username: order
            for _, _, username, order in COUNCIL_LEADERS
        }
        position_by_username = {
            username: position
            for _, position, username, _ in COUNCIL_LEADERS
        }
        for leader in existing_leaders:
            if leader.telegram_username in order_by_username:
                leader.sort_order = order_by_username[leader.telegram_username]
            if (
                leader.telegram_username in LEGACY_COUNCIL_LEADER_POSITIONS
                and leader.position
                == LEGACY_COUNCIL_LEADER_POSITIONS[leader.telegram_username]
            ):
                leader.position = position_by_username[leader.telegram_username]
        return
    for full_name, position, username, order in COUNCIL_LEADERS:
        session.add(
            CouncilLeader(
                full_name=full_name,
                position=position,
                telegram_username=username,
                sort_order=order,
            )
        )


async def seed_organizations(session) -> None:
    existing_count = await session.scalar(select(StudentOrganization))
    if existing_count:
        return

    session.add(
        StudentOrganization(
            category=OrgCategory.NSO.value,
            name="НСО Финансового факультета",
            description="Информация будет добавлена администратором.",
            sort_order=0,
        )
    )
    for i, name in enumerate(PENDING_CLUBS):
        session.add(
            StudentOrganization(
                category=OrgCategory.CLUB.value,
                name=name,
                description="Существование организации требует подтверждения. "
                "Раздел будет заполнен после уточнения информации.",
                sort_order=i,
                is_active=False,
            )
        )
    for i, name in enumerate(COMMITTEES):
        session.add(
            StudentOrganization(
                category=OrgCategory.COMMITTEE.value,
                name=name,
                description="Описание будет добавлено администратором.",
                sort_order=i,
            )
        )
    session.add(
        StudentOrganization(
            category=OrgCategory.CREATIVE.value,
            name="Творческие коллективы и студии",
            description="Подробнее — в группе УВР Финуниверситета.",
            link="https://m.vk.ru/@uvr.finuniversity-tvorcheskie-kollektivy-i-studii",
            sort_order=0,
        )
    )


async def migrate_legacy_responses(session) -> None:
    """Перенести единственный старый response_text в историю ответов."""
    legacy_requests = await session.scalars(
        select(Request).where(
            Request.response_text.is_not(None),
            Request.admin_id.is_not(None),
        )
    )
    for request in legacy_requests:
        existing = await session.scalar(
            select(RequestResponse.id).where(RequestResponse.request_id == request.id).limit(1)
        )
        if existing is None:
            session.add(
                RequestResponse(
                    request_id=request.id,
                    admin_id=request.admin_id,
                    text=request.response_text,
                    status=RequestResponseStatus.SENT.value,
                    source_message_id=None,
                    sent_at=request.closed_at or request.taken_at,
                )
            )

    # Если процесс завершился между claim и Telegram API, черновик можно
    # повторить после перезапуска.
    await session.execute(
        update(RequestResponse)
        .where(RequestResponse.status == RequestResponseStatus.SENDING.value)
        .values(status=RequestResponseStatus.FAILED.value)
    )


async def run_seed() -> None:
    await init_db()
    async with async_session_maker() as session:
        await seed_admins(session)
        await seed_content_sections(session)
        await seed_council_leaders(session)
        await seed_organizations(session)
        await migrate_legacy_responses(session)
        await session.commit()
    logger.info("Инициализация БД завершена.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())
