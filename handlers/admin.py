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
        await callback.answer()
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

# 2) Просмотр списка пользователей
@router.callback_query(F.data == "view_users")
async def view_users(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to view users without admin rights.")
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await callback.message.answer("Пользователей нет.")
        logger.info(f"No users found for admin {callback.from_user.id}.")
        await callback.answer()
        return

    text = "<b>Список пользователей:</b>\n\n"
    for u in users:
        text += f"ID: {u.user_id} | Имя: {u.name or 'Не указано'} | Роль: {u.role or 'user'} | Ранг: {getattr(u, 'user_rank', 'не назначен')}\n"

    await callback.message.answer(text)
    await callback.answer()

# 3) Назначение админа (только супер-админ)
@router.callback_query(F.data == "assign_admin")
async def assign_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to assign admin without superadmin rights.")
        return
    await callback.message.answer("Введите ID пользователя, чтобы назначить администратором:")
    await state.set_state("assign_admin_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "assign_admin_waiting_for_user_id")
async def assign_admin_confirm(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)  # Преобразуем введенный текст в ID
    except ValueError:
        await message.answer("Введите корректный ID пользователя.")  # В случае ошибки
        logger.error(f"Invalid user ID input by {message.from_user.id}: {message.text}")
        return  # Ожидаем корректный ввод

    # Проверка существования пользователя
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
        else:
            user.role = "admin"
            session.add(user)
            await session.commit()
            await message.answer(f"Пользователь {user_id} назначен администратором.")
            logger.info(f"User {message.from_user.id} assigned admin role to user {user_id}.")
    await state.clear()  # Очищаем состояние после завершения

# 4) Смена ранга пользователя
RANKS = {
    "прихлебала": 0.6,
    "лошадь": 0.7,
    "музыкант": 0.8
}

@router.callback_query(F.data == "change_rank")
async def change_rank_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to change rank without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя, чтобы изменить его ранг:")
    await state.set_state("change_rank_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "change_rank_waiting_for_user_id")
async def change_rank_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID пользователя.")  # В случае ошибки
        logger.error(f"Invalid user ID input by {message.from_user.id}: {message.text}")
        return

    # Если пользователь найден, продолжаем
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()  # Очистим состояние, чтобы не сбить дальнейшие переходы
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
            return

        await message.answer(f"Выберите ранг для пользователя {user_id}:\n" + "\n".join(RANKS.keys()))
        await state.update_data(user_id=user_id)
        await state.set_state("change_rank_waiting_for_rank")  # Переход к следующему состоянию

@router.message(F.state == "change_rank_waiting_for_rank")
async def change_rank_select(message: types.Message, state: FSMContext):
    rank = message.text.lower()
    if rank not in RANKS:
        await message.answer(f"Неверный ранг. Выберите из: {', '.join(RANKS.keys())}")
        logger.error(f"Invalid rank selection by {message.from_user.id}: {rank}")
        return

    data = await state.get_data()
    user_id = data.get("user_id")

    # Изменяем ранг пользователя
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            user.user_rank = rank
            session.add(user)
            await session.commit()
            await message.answer(f"Ранг пользователя {user_id} изменен на {rank}.")
            logger.info(f"User {message.from_user.id} changed rank of user {user_id} to {rank}.")
    await state.clear()

# 5) Выдача и вычитание выплат
@router.callback_query(F.data == "manage_payout")
async def manage_payout_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to manage payouts without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя для управления выплатой:")
    await state.set_state("payout_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "payout_waiting_for_user_id")
async def payout_get_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        logger.error(f"Invalid user ID input for payout by {message.from_user.id}: {message.text}")
        return
    await state.update_data(user_id=user_id)
    await message.answer("Введите сумму выплаты (для вычета используйте отрицательное число):")
    await state.set_state("payout_waiting_for_amount")

@router.message(F.state == "payout_waiting_for_amount")
async def payout_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("Введите корректную сумму (целое число).")
        logger.error(f"Invalid payout amount input by {message.from_user.id}: {message.text}")
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    admin_id = message.from_user.id
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
            return
        # Обновляем баланс с учетом ранга
        rank = getattr(user, "user_rank", None)
        percent = RANKS.get(rank, 1)
        payout_amount = int(amount * percent)
        user.payout = (user.payout or 0) + payout_amount

        # Сохраняем запись выплаты
        payout_record = Payout(user_id=user_id, amount=amount, issued_by=admin_id)
        session.add(user)
        session.add(payout_record)
        await session.commit()
        await message.answer(f"Выплата {amount} USDT обновлена (учет ранга: {percent * 100}%). Новый баланс: {user.payout} USDT.")
        logger.info(f"Payout of {amount} USDT for user {user_id} processed by {admin_id}. New balance: {user.payout} USDT.")
    await state.clear()

# 6) Бан и заморозка пользователя
@router.callback_query(F.data == "ban_user")
async def ban_user_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to ban user without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя для бана или заморозки:")
    await state.set_state("ban_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "ban_waiting_for_user_id")
async def ban_user_get_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        logger.error(f"Invalid user ID input for ban by {message.from_user.id}: {message.text}")
        return
    await state.update_data(user_id=user_id)
    await message.answer("Введите количество дней для заморозки (0 — чтобы разбанить):")
    await state.set_state("ban_waiting_for_days")

@router.message(F.state == "ban_waiting_for_days")
async def ban_user_set_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("Введите корректное число дней.")
        logger.error(f"Invalid number of days input for ban by {message.from_user.id}: {message.text}")
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
            return
        if days == 0:
            user.banned_until = None
            await message.answer(f"Пользователь {user_id} разбанен.")
            logger.info(f"User {user_id} unbanned by admin {message.from_user.id}.")
        else:
            user.banned_until = datetime.utcnow() + timedelta(days=days)
            await message.answer(f"Пользователь {user_id} заблокирован на {days} дней.")
            logger.info(f"User {user_id} banned for {days} days by admin {message.from_user.id}.")
        session.add(user)
        await session.commit()
    await state.clear()

# 7) Постинг в бота
@router.callback_query(F.data == "post_bot")
async def post_bot_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to post in bot without admin rights.")
        return
    await callback.message.answer("Введите текст поста для бота:")
    await state.set_state("post_bot_waiting_text")
    await callback.answer()

@router.message(F.state == "post_bot_waiting_text")
async def post_bot_send(message: types.Message, state: FSMContext):
    text = message.text
    # Здесь можно добавить рассылку всем пользователям из базы, пока просто ответ
    await message.answer("Пост опубликован в боте:\n\n" + text)
    logger.info(f"Post sent to bot by admin {message.from_user.id}: {text}")
    await state.clear()

# 8) Постинг в канал
@router.callback_query(F.data == "post_channel")
async def post_channel_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to post in channel without admin rights.")
        return
    await callback.message.answer("Введите текст поста для канала:")
    await state.set_state("post_channel_waiting_text")
    await callback.answer()

@router.message(F.state == "post_channel_waiting_text")
async def post_channel_send(message: types.Message, state: FSMContext):
    text = message.text
    for ch_id in CHANNEL_IDS:
        try:
            await message.bot.send_message(ch_id, text)
        except Exception as e:
            logger.error(f"Failed to post in channel {ch_id}: {e}")
    await message.answer("Пост опубликован в канале.")
    logger.info(f"Post sent to channels by admin {message.from_user.id}: {text}")
    await state.clear()
