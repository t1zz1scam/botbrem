from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user_by_id, update_user_name, update_user_wallet, get_top_users, get_total_earned_today, SessionLocal, Application, is_user_banned
from datetime import datetime

router = Router()

def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="💼 Изменить кошелек", callback_data="edit_wallet")],
        [InlineKeyboardButton(text="📊 Топ пользователей", callback_data="top_users")],
        [InlineKeyboardButton(text="💰 Общий заработок за сегодня", callback_data="total_today")],
    ])

@router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user = await get_user_by_id(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    if await is_user_banned(user.user_id):
        await message.answer("Вы заблокированы и не можете пользоваться ботом.")
        return

    text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"📡 Имя: {user.name or 'не указано'}\n"
        f"💼 Кошелек: {user.contact or 'не указан'}\n"
        f"💸 Заработано: {user.payout:.2f} USDT\n"
        f"🎖 Ранг: {user.rank or 'Новичок'}\n"
        f"🔰 Роль: {user.role or 'user'}"
    )
    await message.answer(text, reply_markup=profile_kb())
