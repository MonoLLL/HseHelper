from aiogram.fsm.state import State, StatesGroup


class AskFlow(StatesGroup):
    waiting_for_confirm = State()
    waiting_for_files = State()