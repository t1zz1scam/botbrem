import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Application, SessionLocal, User, Payout
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime, timedelta
from config import CHANNEL_IDS

router = Router()

# Настройка логирования (вывод в консоль)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Клавиатура админ-панели
admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[ 
    [InlineKeyboardButton(text="📬 Заявки", callback_data="view_applications")], 
    [InlineKeyboardButton(text="👥 Список пользователей", callback_data="view_users")],
    [InlineKeyboardButton(text="➕ Назначить админа", callback_data="assign_admin")],
    [InlineKeyboardButton(text="🔧 Изменить ранг пользователя", callback_data="change_rank")],
    [InlineKeyboardButton(text="💰 Выдача / Вычитание выплат", callback_data="manage_payout")],
    [InlineKeyboardButton(text="🚫 Бан / Заморозка пользователя", callback_data="ban_user")],
    [InlineKeyboardButton(text="📝 Пост в бота", callback_data="post_bot")],
    [InlineKeyboardButton(text="📢 Пост в канал", callback_data="post_channel")],
])

# Утилиты проверки роли
async def is_admin(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user and user.role in ("admin", "superadmin")

async def is_superadmin(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user and user.role == "superadmin"

# Показываем админ-панель
@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        logger.warning(f"User {message.from_user.id} tried to access admin panel without permissions.")
        return
    await message.answer("👷‍♂️ Админ-панель", reply_markup=admin_panel_kb)
    logger.info(f"Admin panel accessed by {message.from_user.id}")

# 1) Просмотр заявок
@router.callback_query(F.data == "view_applications")
async def view_applications(callback: types.CallbackQuery):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to view applications without admin rights.")
        return
    async with SessionLocal() as session:
        result = await session.execute(select(Application).where(Application.status == "pending"))
        applications = result.scalars().all()

    if not applications:
        await callback.message.answer("Нет новых заявок.")
        logger.info(f"No new applications available for {callback.from_user.id}.")
        return

    for app in applications:
        text = (
            f"<b>Заявка от пользователя {app.user_id}</b>\n\n"
            f"Сообщение:\n{app.message}\n\n"
            f"Статус: {app.status}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{app.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{app.id}")
            ]
        ])
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

# 3) Назначение админа (только супер-админ)
@router.callback_query(F.data == "assign_admin")
async def assign_admin_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_superadmin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to assign admin without superadmin rights.")
        return
    await callback.message.answer("Введите ID пользователя, чтобы назначить администратором:")
    await state.set_state("assign_admin_waiting_for_user_id")

@router.message(F.state == "assign_admin_waiting_for_user_id")
async def assign_admin_confirm(message: types.Message, state: FSMContext):
    """
    Подтверждение назначения админа по ID пользователя.
    Обрабатываем ID, игнорируя тип сущности.
    """
    # Извлекаем только текст без сущностей
    user_id = message.text.strip()
    
    # Если текст был распознан как номер телефона, убираем его
    if message.entities:
        # Если есть сущности, проверяем, что это номер телефона
        if message.entities[0].type == 'phone_number':
            user_id = user_id.replace(message.text, '').strip()
    
    # Проверяем, что введен числовой ID
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
    
    # Ищем пользователя в базе
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
        else:
            # Если пользователь найден, назначаем его администратором
            user.role = "admin"
            session.add(user)
            await session.commit()
            await message.answer(f"Пользователь {user_id} назначен администратором.")
            logger.info(f"User {message.from_user.id} assigned admin role to user {user_id}.")
    
    await state.clear()
