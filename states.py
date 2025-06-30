from aiogram.fsm.state import StatesGroup, State

class PayoutForm(StatesGroup):
    waiting_for_user_id = State()
