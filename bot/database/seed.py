"""
Первичное заполнение БД:
  * начальные администраторы из .env (INITIAL_ADMIN_ID);
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

from sqlalchemy import select

from config import settings
from database.engine import async_session_maker, init_db
from database.models import (
    Admin,
    ContentSection,
    CouncilLeader,
    OrgCategory,
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
    ("Летуновская Екатерина", "Первый Заместитель Председателя", "katrina007_0", 1),
    ("Мазур Елизавета", "Заместитель председателя по Проектной деятельности", "dwimddd", 2),
    ("Андреев Сергей", "Заместитель председателя по Учебно-Социальной деятельности", "foxssert", 3),
    ("Ефимов Мирон", "Руководитель Направления Внешних Связей", "mironefimov", 4),
    ("Дорохина Варвара", "Руководитель Информационного Направления", "ghtbrn", 5),
    ("Семенов Дмитрий", "Руководитель Направления Развития и Корпоративной Культуры", "preciouslittlediamondd", 6),
    ("Беляева Анастасия", "Секретарь", "atnnasy", 7),
]

# Комитеты прямо перечислены в ТЗ (расшифровку названий и описание
# заказчик предоставит позже — контент не придумываем).
COMMITTEES = ["КВС", "УСК", "ИК", "ПК"]

# Организации, чьё существование в ТЗ помечено как "требует подтверждения" —
# создаём как неактивные заготовки (is_active=False), чтобы админ мог
# включить/заполнить их позже, когда информация подтвердится.
PENDING_CLUBS = ["Клуб молодого финансиста", "Предпринимательский клуб"]


async def seed_admins(session) -> None:
    for admin_id in settings.initial_admin_ids:
        existing = await session.scalar(select(Admin).where(Admin.telegram_id == admin_id))
        if not existing:
            session.add(Admin(telegram_id=admin_id, added_by=None))
            logger.info("Добавлен начальный администратор: %s", admin_id)


async def seed_content_sections(session) -> None:
    for key, title, body in CONTENT_SECTIONS:
        existing = await session.scalar(select(ContentSection).where(ContentSection.key == key))
        if not existing:
            session.add(ContentSection(key=key, title=title, body=body))


async def seed_council_leaders(session) -> None:
    existing_count = await session.scalar(select(CouncilLeader))
    if existing_count:
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


async def run_seed() -> None:
    await init_db()
    async with async_session_maker() as session:
        await seed_admins(session)
        await seed_content_sections(session)
        await seed_council_leaders(session)
        await seed_organizations(session)
        await session.commit()
    logger.info("Инициализация БД завершена.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())
