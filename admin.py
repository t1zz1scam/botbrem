from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from config import SUPER_ADMINS
from keyboards import admin_panel_kb

router = Router()

# Обработка нажатия на "🛠 Админ-панель"
@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in SUPER_ADMINS:
        await message.answer("У вас нет доступа к админ-панели.")
        return
    await message.answer("<b>🛠 Админ-панель</b>\nВыберите действие:", reply_markup=admin_panel_kb)

# Обработка callback-кнопок в админке

@router.callback_query(F.data == "view_applications")
async def view_applications(callback: CallbackQuery):
    # Заглушка — можно подключить реальную логику
    await callback.message.answer("📬 Здесь будут отображаться заявки.")
    await callback.answer()

@router.callback_query(F.data == "manage_payouts")
async def manage_payouts(callback: CallbackQuery):
    await callback.message.answer("💸 Здесь вы можете управлять выплатами.")
    await callback.answer()

@router.callback_query(F.data == "post_to_channels")
async def post_to_channels(callback: CallbackQuery):
    await callback.message.answer("📰 Здесь можно опубликовать пост в канал.")
    await callback.answer()

@router.callback_query(F.data == "view_stats")
async def view_stats(callback: CallbackQuery):
    await callback.message.answer("📊 Здесь будет статистика.")
    await callback.answer()
