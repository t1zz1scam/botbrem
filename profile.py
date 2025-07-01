from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from database import get_user_by_id, update_user_name, update_user_wallet, get_top_users, get_total_earned_today, SessionLocal, Application

router = Router()

class EditProfile(StatesGroup):
    name = State()
    wallet = State()

class ApplicationForm(StatesGroup):
    message = State()

def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏ Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="💼 Изменить кошелек", callback_data="edit_wallet")],
        [InlineKeyboardButton(text="📊 Топ пользователей", callback_data="top_users")],
        [InlineKeyboardButton(text="💰 Общий заработок за сегодня", callback_data="total_today")],
        [InlineKeyboardButton(text="📋 Подать заявку", callback_data="apply")]
    ])

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📋 Подать заявку")],
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Добро пожаловать в бота.\nВыберите действие ниже:",
        reply_markup=main_menu
    )

@router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    user = await get_user_by_id(user_id)

    text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"📡 Имя: {user.name or 'не указано'}\n"
        f"💼 Кошелек: {user.contact or 'не указан'}\n"
        f"💸 Заработано: {user.payout:.2f} USDT\n"
        f"🎖 Звание: {user.role or 'Новичок'}"
    )
    await message.answer(text, reply_markup=profile_kb())

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

@router.callback_query(F.data == "top_users")
async def top_users(callback: types.CallbackQuery):
    top = await get_top_users("day")
    if not top:
        text = "Нет данных."
    else:
        text = "<b>🏆 Топ пользователей за сегодня:</b>\n\n"
        for i, row in enumerate(top, 1):
            text += f"{i}. {row['name']} — {row['earned']:.2f} USDT\n"
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "total_today")
async def total_today(callback: types.CallbackQuery):
    total = await get_total_earned_today()
    text = f"💰 Общая сумма заработка всех пользователей за сегодня: {total or 0:.2f} USDT"
    await callback.message.answer(text)
    await callback.answer()

@router.message(F.text == "📋 Подать заявку")
async def start_application(message: types.Message, state: FSMContext):
    await message.answer("Опишите вашу заявку, пожалуйста:")
    await state.set_state(ApplicationForm.message)

@router.message(ApplicationForm.message)
async def save_application(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    async with SessionLocal() as session:
        new_app = Application(user_id=user_id, message=text, status="pending")
        session.add(new_app)
        await session.commit()
    await message.answer("Ваша заявка принята! Ожидайте обработки.")
    await state.clear()
