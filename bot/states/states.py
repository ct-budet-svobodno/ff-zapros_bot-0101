"""
Группы состояний FSM.

Выбор анонимности/курса/корпуса реализован через inline-кнопки (callback),
поэтому формально FSM-состояние там не обязательно, но мы всё равно
переключаем состояние на каждом шаге — это упрощает обработку "неожиданных"
сообщений (см. utils/fallback) и защищает от гонок, если пользователь
одновременно тыкает старые кнопки.
"""
from aiogram.fsm.state import State, StatesGroup


class RequestForm(StatesGroup):
    choosing_anonymity = State()
    choosing_course = State()
    choosing_building = State()
    entering_question = State()
    preview = State()


class SectionEdit(StatesGroup):
    """Редактирование "длинного" текста (история факультета и т.п.)."""
    entering_text = State()
    preview = State()


class FacultyAdminForm(StatesGroup):
    entering_full_name = State()
    entering_position = State()
    entering_contact = State()
    entering_photo = State()
    preview = State()


class FacultyAdminEditForm(StatesGroup):
    """Редактирование одного поля существующей записи администрации факультета."""
    entering_value = State()
    preview = State()


class OrganizationForm(StatesGroup):
    choosing_category = State()
    entering_name = State()
    entering_description = State()
    entering_link = State()
    preview = State()


class OrganizationEditForm(StatesGroup):
    """Редактирование одного поля существующей студенческой организации."""
    entering_value = State()
    preview = State()


class CouncilLeaderForm(StatesGroup):
    entering_full_name = State()
    entering_position = State()
    entering_username = State()
    entering_photo = State()
    preview = State()


class CouncilLeaderEditForm(StatesGroup):
    """Редактирование одного поля существующего руководителя Студсовета."""
    entering_value = State()
    preview = State()


class DigestForm(StatesGroup):
    entering_month = State()
    entering_title = State()
    entering_text = State()
    preview = State()


class DigestEdit(StatesGroup):
    entering_text = State()
    preview = State()


class DocumentForm(StatesGroup):
    entering_title = State()
    entering_description = State()
    uploading_pdf = State()
    preview = State()


class DocumentEdit(StatesGroup):
    entering_title = State()
    entering_description = State()
    uploading_pdf = State()


class AdminManageForm(StatesGroup):
    """Добавление нового администратора по Telegram ID."""
    entering_telegram_id = State()
