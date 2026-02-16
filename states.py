from aiogram.fsm.state import StatesGroup, State


class LeadForm(StatesGroup):
    name = State()
    phone = State()
    email = State()
    budget = State()
    region = State()
    timeframe = State()
    contacted = State()
