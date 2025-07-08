import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Application, SessionLocal, User, Payout
from sqlalchemy.future import select
from datetime import datetime, timedelta
from config import CHANNEL_IDS

router = Router()

# Настройка логирования (вывод в консоль)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Обработчик для получения номера телефона
@router.message(F.entities)
async def handle_phone_number(message: types.Message):
    # Проверяем, есть ли в сообщении телефон
    phone_entity = next((entity for entity in message.entities if entity.type == 'phone_number'), None)
    if phone_entity:
        phone_number = message.text[phone_entity.offset:phone_entity.offset + phone_entity.length]
        await message.answer(f"Вы отправили номер телефона: {phone_number}")
        logger.info(f"Phone number received: {phone_number} from user {message.from_user.id}")

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

# 2) Одобрение или отклонение заявки
@router.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: types.CallbackQuery):
    app_id = callback.data.split("_")[1]
    async with SessionLocal() as session:
        result = await session.execute(select(Application).where(Application.id == app_id))
        application = result.scalar_one_or_none()
        if application:
            application.status = "approved"
            session.add(application)
            await session.commit()
            await callback.message.answer(f"Заявка от пользователя {application.user_id} одобрена.")
            logger.info(f"Application {app_id} approved by {callback.from_user.id}.")
        else:
            await callback.message.answer("Заявка не найдена.")
            logger.warning(f"Application {app_id} not found.")
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: types.CallbackQuery):
    app_id = callback.data.split("_")[1]
    async with SessionLocal() as session:
        result = await session.execute(select(Application).where(Application.id == app_id))
        application = result.scalar_one_or_none()
        if application:
            application.status = "rejected"
            session.add(application)
            await session.commit()
            await callback.message.answer(f"Заявка от пользователя {application.user_id} отклонена.")
            logger.info(f"Application {app_id} rejected by {callback.from_user.id}.")
        else:
            await callback.message.answer("Заявка не найдена.")
            logger.warning(f"Application {app_id} not found.")
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
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
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
    await state.clear()

# 4) Смена ранга пользователя
@router.callback_query(F.data == "change_rank")
async def change_rank_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to change rank without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя, чтобы изменить его ранг:")
    await state.set_state("change_rank_waiting_for_user_id")

@router.message(F.state == "change_rank_waiting_for_user_id")
async def change_rank_user_id(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
        else:
            await message.answer(f"Выберите новый ранг для пользователя {user_id}:")
            await state.update_data(user_id=user_id)
            await state.set_state("change_rank_waiting_for_rank")

@router.message(F.state == "change_rank_waiting_for_rank")
async def change_rank_select(message: types.Message, state: FSMContext):
    rank = message.text.strip().lower()
    if rank not in ["прихлебала", "лошадь", "музыкант"]:
        await message.answer("Неверный ранг. Выберите из: прихлебала, лошадь, музыкант.")
        return

    data = await state.get_data()
    user_id = data.get("user_id")
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            user.user_rank = rank
            session.add(user)
            await session.commit()
            await message.answer(f"Ранг пользователя {user_id} изменен на {rank}.")
            logger.info(f"User {message.from_user.id} changed rank for {user_id} to {rank}.")
    await state.clear()

# 5) Бан / Заморозка пользователя
@router.callback_query(F.data == "ban_user")
async def ban_user_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to ban user without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя, чтобы заблокировать или разморозить:")
    await state.set_state("ban_user_waiting_for_user_id")

@router.message(F.state == "ban_user_waiting_for_user_id")
async def ban_user_confirm(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for admin {message.from_user.id}.")
        else:
            user.banned = not user.banned
            session.add(user)
            await session.commit()
            status = "заблокирован" if user.banned else "разморожен"
            await message.answer(f"Пользователь {user_id} {status}.")
            logger.info(f"User {message.from_user.id} banned/unbanned user {user_id}.")
    await state.clear()

# 6) Выдача / Вычитание выплат
@router.callback_query(F.data == "manage_payout")
async def manage_payout_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to manage payouts without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя для управления выплатами:")
    await state.set_state("manage_payout_waiting_for_user_id")

@router.message(F.state == "manage_payout_waiting_for_user_id")
async def manage_payout_amount(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for payout management.")
        else:
            await message.answer(f"Введите сумму выплаты для пользователя {user_id}:")
            await state.update_data(user_id=user_id)
            await state.set_state("manage_payout_waiting_for_amount")

@router.message(F.state == "manage_payout_waiting_for_amount")
async def manage_payout_confirm(message: types.Message, state: FSMContext):
    amount = message.text.strip()
    if not amount.isdigit():
        await message.answer("Введите корректную сумму.")
        return

    amount = int(amount)
    data = await state.get_data()
    user_id = data.get("user_id")

    # Расчет выплаты в зависимости от ранга
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            rank_factor = 0.6 if user.user_rank == "прихлебала" else 0.7 if user.user_rank == "лошадь" else 0.8
            payout = amount * rank_factor
            user.balance += payout
            session.add(user)
            await session.commit()
            await message.answer(f"Выплата {payout} выдана пользователю {user_id}.")
            logger.info(f"User {message.from_user.id} made a payout of {payout} to {user_id}.")
    await state.clear()

# 7) Отмена выплаты
@router.callback_query(F.data == "cancel_payout")
async def cancel_payout_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to cancel payout without admin rights.")
        return
    await callback.message.answer("Введите ID пользователя для отмены выплаты:")
    await state.set_state("cancel_payout_waiting_for_user_id")

@router.message(F.state == "cancel_payout_waiting_for_user_id")
async def cancel_payout_confirm(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("Введите корректный ID пользователя.")
        return

    user_id = int(user_id)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            logger.warning(f"User {user_id} not found for payout cancellation.")
        else:
            await message.answer(f"Введите сумму, которую нужно отменить для пользователя {user_id}:")
            await state.update_data(user_id=user_id)
            await state.set_state("cancel_payout_waiting_for_amount")

@router.message(F.state == "cancel_payout_waiting_for_amount")
async def cancel_payout_confirm_amount(message: types.Message, state: FSMContext):
    amount = message.text.strip()
    if not amount.isdigit():
        await message.answer("Введите корректную сумму.")
        return

    amount = int(amount)
    data = await state.get_data()
    user_id = data.get("user_id")

    # Отменяем выплату
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            user.balance -= amount
            session.add(user)
            await session.commit()
            await message.answer(f"Выплата в размере {amount} отменена для пользователя {user_id}.")
            logger.info(f"User {message.from_user.id} cancelled payout of {amount} for {user_id}.")
    await state.clear()

# 8) Пост в бота
@router.callback_query(F.data == "post_bot")
async def post_to_bot_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to post to bot without admin rights.")
        return
    await callback.message.answer("Введите текст для поста в бота:")
    await state.set_state("post_bot_waiting_for_text")

@router.message(F.state == "post_bot_waiting_for_text")
async def post_to_bot_confirm(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return

    # Отправляем сообщение всем пользователям бота
    async with SessionLocal() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()

        for user in users:
            await bot.send_message(user.user_id, text)
    await message.answer("Пост опубликован в боте.")
    logger.info(f"User {message.from_user.id} posted to bot.")

    await state.clear()

# 9) Пост в канал
@router.callback_query(F.data == "post_channel")
async def post_to_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        logger.warning(f"User {callback.from_user.id} tried to post to channel without admin rights.")
        return
    await callback.message.answer("Введите текст для поста в канал:")
    await state.set_state("post_channel_waiting_for_text")

@router.message(F.state == "post_channel_waiting_for_text")
async def post_to_channel_confirm(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return

    # Отправляем сообщение в канал
    for channel_id in CHANNEL_IDS:
        await bot.send_message(channel_id, text)
    await message.answer("Пост опубликован в канал.")
    logger.info(f"User {message.from_user.id} posted to channel.")

    await state.clear()
