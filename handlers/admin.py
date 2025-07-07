from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Application, SessionLocal, User, Payout
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime

router = Router()

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
        return
    await message.answer("👷‍♂️ Админ-панель", reply_markup=admin_panel_kb)

# 1) Просмотр заявок
@router.callback_query(F.data == "view_applications")
async def view_applications(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with SessionLocal() as session:
        result = await session.execute(select(Application).where(Application.status == "pending"))
        applications = result.scalars().all()

    if not applications:
        await callback.message.answer("Нет новых заявок.")
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

@router.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id

    async with SessionLocal() as session:
        await session.execute(
            update(Application).where(Application.id == app_id).values(
                status="approved",
                resolved_by=admin_id,
                resolved_at=datetime.utcnow()
            )
        )
        await session.commit()
        app = await session.get(Application, app_id)

    await callback.message.answer(f"Заявка #{app_id} одобрена.")
    try:
        await callback.bot.send_message(app.user_id, "Ваша заявка одобрена администратором!")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    app_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id

    async with SessionLocal() as session:
        await session.execute(
            update(Application).where(Application.id == app_id).values(
                status="rejected",
                resolved_by=admin_id,
                resolved_at=datetime.utcnow()
            )
        )
        await session.commit()
        app = await session.get(Application, app_id)

    await callback.message.answer(f"Заявка #{app_id} отклонена.")
    try:
        await callback.bot.send_message(app.user_id, "Ваша заявка отклонена администратором.")
    except Exception:
        pass
    await callback.answer()

# 2) Просмотр списка пользователей
@router.callback_query(F.data == "view_users")
async def view_users(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await callback.message.answer("Пользователей нет.")
        await callback.answer()
        return

    text = "<b>Список пользователей:</b>\n\n"
    for u in users:
        text += f"ID: {u.user_id} | Имя: {u.name or 'Не указано'} | Роль: {u.role or 'user'} | Ранг: {getattr(u, 'rank', 'не назначен')}\n"

    await callback.message.answer(text)
    await callback.answer()

# 3) Назначение админа (только супер-админ)
@router.callback_query(F.data == "assign_admin")
async def assign_admin_start(callback: types.CallbackQuery, state=None):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя, чтобы назначить администратором:")
    await state.set_state("assign_admin_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "assign_admin_waiting_for_user_id")
async def assign_admin_confirm(message: types.Message, state):
    user_id = int(message.text)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
        else:
            user.role = "admin"
            session.add(user)
            await session.commit()
            await message.answer(f"Пользователь {user_id} назначен администратором.")
    await state.clear()

# 4) Смена ранга пользователя
RANKS = {
    "прихлебала": 0.6,
    "лошадь": 0.7,
    "музыкант": 0.8
}

@router.callback_query(F.data == "change_rank")
async def change_rank_start(callback: types.CallbackQuery, state=None):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя, чтобы изменить его ранг:")
    await state.set_state("change_rank_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "change_rank_waiting_for_user_id")
async def change_rank_user_id(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID пользователя.")
        return
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        await message.answer(f"Выберите ранг для пользователя {user_id}:\n" + "\n".join(RANKS.keys()))
        await state.update_data(user_id=user_id)
        await state.set_state("change_rank_waiting_for_rank")

@router.message(F.state == "change_rank_waiting_for_rank")
async def change_rank_select(message: types.Message, state):
    rank = message.text.lower()
    if rank not in RANKS:
        await message.answer(f"Неверный ранг. Выберите из: {', '.join(RANKS.keys())}")
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            setattr(user, "rank", rank)
            session.add(user)
            await session.commit()
            await message.answer(f"Ранг пользователя {user_id} изменен на {rank}.")
    await state.clear()

# 5) Выдача и вычитание выплат
@router.callback_query(F.data == "manage_payout")
async def manage_payout_start(callback: types.CallbackQuery, state=None):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя для управления выплатой:")
    await state.set_state("payout_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "payout_waiting_for_user_id")
async def payout_get_user_id(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await message.answer("Введите сумму выплаты (для вычета используйте отрицательное число):")
    await state.set_state("payout_waiting_for_amount")

@router.message(F.state == "payout_waiting_for_amount")
async def payout_get_amount(message: types.Message, state):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("Введите корректную сумму (целое число).")
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    admin_id = message.from_user.id
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        # Обновляем баланс с учетом ранга
        rank = getattr(user, "rank", None)
        percent = RANKS.get(rank, 1)
        payout_amount = int(amount * percent)
        user.payout = (user.payout or 0) + payout_amount

        # Сохраняем запись выплаты
        payout_record = Payout(user_id=user_id, amount=amount, issued_by=admin_id)
        session.add(user)
        session.add(payout_record)
        await session.commit()
        await message.answer(f"Выплата {amount} USDT обновлена (учет ранга: {percent * 100}%). Новый баланс: {user.payout} USDT.")
    await state.clear()

# 6) Бан и заморозка пользователя
@router.callback_query(F.data == "ban_user")
async def ban_user_start(callback: types.CallbackQuery, state=None):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя для бана или заморозки:")
    await state.set_state("ban_waiting_for_user_id")
    await callback.answer()

@router.message(F.state == "ban_waiting_for_user_id")
async def ban_user_get_id(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный ID.")
        return
    await state.update_data(user_id=user_id)
    await message.answer("Введите количество дней для заморозки (0 — чтобы разбанить):")
    await state.set_state("ban_waiting_for_days")

@router.message(F.state == "ban_waiting_for_days")
async def ban_user_set_days(message: types.Message, state):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("Введите корректное число дней.")
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        if days == 0:
            user.banned_until = None
            await message.answer(f"Пользователь {user_id} разбанен.")
        else:
            from datetime import datetime, timedelta
            user.banned_until = datetime.utcnow() + timedelta(days=days)
            await message.answer(f"Пользователь {user_id} заблокирован на {days} дней.")
        session.add(user)
        await session.commit()
    await state.clear()

# 7) Постинг в бота
@router.callback_query(F.data == "post_bot")
async def post_bot_start(callback: types.CallbackQuery, state=None):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите текст поста для бота:")
    await state.set_state("post_bot_waiting_text")
    await callback.answer()

@router.message(F.state == "post_bot_waiting_text")
async def post_bot_send(message: types.Message, state):
    text = message.text
    # Отправляем всем пользователям (если надо, можно сделать рассылку)
    await message.answer("Пост опубликован в боте:\n\n" + text)
    # Для демонстрации — просто ответили, можно расширить на рассылку
    await state.clear()

# 8) Постинг в канал
@router.callback_query(F.data == "post_channel")
async def post_channel_start(callback: types.CallbackQuery, state=None):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите текст поста для канала:")
    await state.set_state("post_channel_waiting_text")
    await callback.answer()

@router.message(F.state == "post_channel_waiting_text")
async def post_channel_send(message: types.Message, state):
    text = message.text
    from config import CHANNEL_IDS
    for ch_id in CHANNEL_IDS:
        try:
            await message.bot.send_message(ch_id, text)
        except Exception:
            pass
    await message.answer("Пост опубликован в канале.")
    await state.clear()
