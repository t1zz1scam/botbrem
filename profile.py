from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

# Импортируем свои функции из БД (тебе нужно реализовать эти функции в database.py)
from database import get_user_by_id, update_user_name, update_user_wallet, get_top_users, get_total_earned_today

router = Router()

# FSM состояния
class EditProfile(StatesGroup):
    name = State()
    wallet = State()

# Клавиатура профиля
def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="💼 Изменить кошелек", callback_data="edit_wallet")],
        [InlineKeyboardButton(text="📊 Топ пользователей", callback_data="top_users")],
        [InlineKeyboardButton(text="💰 Общий заработок за сегодня", callback_data="total_today")]
    ])

# Обработка кнопки "👤 Профиль"
@router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    user = await get_user_by_id(user_id)

    text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"📡 Имя: {user.name}\n"
        f"💼 Кошелек: {user.wallet or 'не указан'}\n"
        f"💸 Заработано: {user.earned:.2f} USDT\n"
        f"🎖 Звание: {user.rank or 'Новичок'}"
    )
    await message.answer(text, reply_markup=profile_kb())

# Обработка изменения имени
@router.callback_query(F.data == "edit_name")
async def edit_name_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое имя:")
    await state.set_state(EditProfile.name)
    await callback.answer()

@router.message(EditProfile.name)
async def save_new_name(message: types.Message, state: FSMContext):
    await update_user_name(message.from_user.id, message.text)
    await message.answer("Имя обновлено")
    await state.clear()

# Обработка изменения кошелька
@router.callback_query(F.data == "edit_wallet")
async def edit_wallet_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новый адрес кошелька:")
    await state.set_state(EditProfile.wallet)
    await callback.answer()

@router.message(EditProfile.wallet)
async def save_new_wallet(message: types.Message, state: FSMContext):
    await update_user_wallet(message.from_user.id, message.text)
    await message.answer("Кошелек обновлен")
    await state.clear()

# Обработка топа пользователей
@router.callback_query(F.data == "top_users")
async def top_users(callback: types.CallbackQuery):
    top = await get_top_users("day")  # можно сделать выбор периода позже
    if not top:
        text = "Нет данных."
    else:
        text = "<b>🏆 Топ пользователей за сегодня:</b>\n\n"
        for i, row in enumerate(top, 1):
            text += f"{i}. {row['name']} — {row['earned']:.2f} USDT\n"
    await callback.message.answer(text)
    await callback.answer()

# Общий заработок
@router.callback_query(F.data == "total_today")
async def total_today(callback: types.CallbackQuery):
    total = await get_total_earned_today()
    text = f"💰 Общая сумма заработка всех пользователей за сегодня: {total or 0:.2f} USDT"
    await callback.message.answer(text)
    await callback.answer()
