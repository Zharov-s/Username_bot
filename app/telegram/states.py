from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    waiting_for_import_file = State()
    waiting_for_lookup_file = State()
