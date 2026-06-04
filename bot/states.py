from aiogram.fsm.state import State, StatesGroup


class AskFlow(StatesGroup):
    waiting_for_confirm = State()
    waiting_for_files = State()
    waiting_for_dialog_draft = State()


class RegistrationFlow(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_faculty = State()
    waiting_for_course = State()
    waiting_for_group = State()


class SiteLoginFlow(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()


class SiteAccessFlow(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
