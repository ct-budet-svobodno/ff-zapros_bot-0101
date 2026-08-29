"""
Модели базы данных.

Используется SQLAlchemy 2.0 (async) ORM. Схема спроектирована так,
чтобы весь пользовательский контент (тексты, персоны, документы, дайджесты,
организации) жил в БД и редактировался через админ-панель, а не в коде.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Пользователи и администраторы
# --------------------------------------------------------------------------

class User(Base):
    """Любой пользователь, писавший боту (нужен для истории обращений)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    requests: Mapped[list["Request"]] = relationship(back_populates="user")


class Admin(Base):
    """Администратор бота. Авторизация строго по telegram_id."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


# --------------------------------------------------------------------------
# Обращения студентов
# --------------------------------------------------------------------------

class RequestStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class Course(str, enum.Enum):
    C1 = "1 курс"
    C2 = "2 курс"
    C3 = "3 курс"
    C4 = "4 курс"
    MASTER = "Магистратура"


class Building(str, enum.Enum):
    KITAY_GOROD = "Китай-город"
    FILI = "Фили"


class Request(Base):
    """Обращение студента."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    course: Mapped[str] = mapped_column(String(32), nullable=False)
    building: Mapped[str] = mapped_column(String(64), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), default=RequestStatus.NEW.value, nullable=False, index=True
    )

    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ID сообщения в рабочей группе — чтобы редактировать его (менять статус в тексте)
    group_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    group_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship(back_populates="requests")
    admin: Mapped["Admin | None"] = relationship()


# --------------------------------------------------------------------------
# Редактируемый контент
# --------------------------------------------------------------------------

class ContentSection(Base):
    """
    Универсальная таблица для «длинных» редактируемых текстов, у которых
    ровно один экземпляр — история факультета, инфо-текст о Студсовете,
    текст про отбор в Студсовет и т.п. Идентифицируется уникальным key.
    """

    __tablename__ = "content_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FacultyAdminPerson(Base):
    """Представитель администрации факультета."""

    __tablename__ = "faculty_admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrgCategory(str, enum.Enum):
    NSO = "НСО Финансового факультета"
    CLUB = "Клубы"
    COMMITTEE = "Комитеты"
    CREATIVE = "Творческие коллективы"
    OTHER = "Другое"


class StudentOrganization(Base):
    """Студенческая организация / комитет / творческий коллектив."""

    __tablename__ = "student_organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CouncilLeader(Base):
    """Руководитель Студенческого совета."""

    __tablename__ = "council_leaders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Digest(Base):
    """Дайджест мероприятий за месяц."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month_label: Mapped[str] = mapped_column(String(32), nullable=False)  # напр. "Август 2026"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Document(Base):
    """PDF-документ (положение, заявление и т.п.)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
