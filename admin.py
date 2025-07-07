from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    Application, SessionLocal,
    update_user_role, update_user_rank,
    add_payout, subtract_payout,
    ban_user, unban_user, is_user_banned,
    get_all_users
)
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime, timedelta

router = Router()

# Проверка прав
async def is_admin(user_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.get("User", user_id)
        if not user:
            return False
        return user.role in ("admin", "superadmin")

async def is_superadmin(user_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.get("User", user_id)
        if not user:
            return False
        return user.role == "superadmin"

# Главное меню админа
def admin_main_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📬 Заявки", callback_data="view_applications")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="view_users")],
        [InlineKeyboardButton(text="✏ Управление пользователями", callback_data="manage_users")],
        [InlineKeyboardButton(text="📢 Посты", callback_data="admin_posts")],
    ])
    return kb

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.message.answer("Админ-панель:", reply_markup=admin_main_kb())
    await callback.answer()

@router.callback_query(F.data == "view_applications")
async def view_applications(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
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
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{app.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{app.id}")
        ]])
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
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
        await callback.answer("Нет доступа.", show_alert=True)
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

@router.callback_query(F.data == "view_users")
async def view_users(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    users = await get_all_users()
    if not users:
        await callback.message.answer("Пользователей нет.")
        await callback.answer()
        return

    text = "<b>Список пользователей:</b>\n\n"
    for u in users:
        ban_status = f" (Забанен до {u.banned_until.strftime('%Y-%m-%d %H:%M')})" if u.banned_until else ""
        text += f"ID: {u.user_id}, Имя: {u.name or '—'}, Роль: {u.role}, Ранг: {u.rank}{ban_status}\n"
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "manage_users")
async def manage_users_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назначить админа", callback_data="assign_admin")],
        [InlineKeyboardButton(text="Сменить ранг", callback_data="change_rank")],
        [InlineKeyboardButton(text="Выплаты", callback_data="manage_payouts")],
        [InlineKeyboardButton(text="Баны", callback_data="manage_bans")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]
    ])
    await callback.message.answer("Управление пользователями:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "assign_admin")
async def assign_admin_start(callback: types.CallbackQuery):
    # Только суперадмин может назначать админов
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("Только суперадмин может назначать админов.", show_alert=True)
        return
    await callback.message.answer("Введите ID пользователя для назначения админом:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "assign_admin_waiting_for_user_id")

@router.message(F.text, state="assign_admin_waiting_for_user_id")
async def assign_admin_process(message: types.Message, state):
    if not await is_superadmin(message.from_user.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID.")
        return
    await update_user_role(user_id, "admin")
    await message.answer(f"Пользователь {user_id} назначен админом.")
    await state.clear()

@router.callback_query(F.data == "change_rank")
async def change_rank_start(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Прихлебала (60%)", callback_data="rank_прихлебала")],
        [InlineKeyboardButton(text="Лошадь (70%)", callback_data="rank_лошадь")],
        [InlineKeyboardButton(text="Музыкант (80%)", callback_data="rank_музыкант")],
        [InlineKeyboardButton(text="Новичок (0%)", callback_data="rank_user")],
        [InlineKeyboardButton(text="Назад", callback_data="manage_users")],
    ])
    await callback.message.answer("Выберите ранг для назначения:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("rank_"))
async def change_rank_process(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rank = callback.data.split("_")[1]
    await callback.message.answer("Введите ID пользователя для смены ранга:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "change_rank_waiting_for_user_id")
    await callback.bot["fsm_storage"].update_data(callback.from_user.id, {"selected_rank": rank})

@router.message(F.text, state="change_rank_waiting_for_user_id")
async def change_rank_finish(message: types.Message, state):
    data = await state.get_data()
    rank = data.get("selected_rank", "user")
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID.")
        return
    try:
        await update_user_rank(user_id, rank)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()
        return
    await message.answer(f"Пользователю {user_id} установлен ранг {rank}.")
    await state.clear()

@router.callback_query(F.data == "manage_payouts")
async def manage_payouts_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выдать выплату", callback_data="payout_add")],
        [InlineKeyboardButton(text="Отнять выплату", callback_data="payout_subtract")],
        [InlineKeyboardButton(text="Назад", callback_data="manage_users")],
    ])
    await callback.message.answer("Управление выплатами:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "payout_add")
async def payout_add_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ID пользователя для выплаты:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "payout_waiting_user_id")
    await callback.bot["fsm_storage"].update_data(callback.from_user.id, {"action": "add"})

@router.callback_query(F.data == "payout_subtract")
async def payout_subtract_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ID пользователя для вычета выплаты:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "payout_waiting_user_id")
    await callback.bot["fsm_storage"].update_data(callback.from_user.id, {"action": "subtract"})

@router.message(F.text, state="payout_waiting_user_id")
async def payout_user_id(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID.")
        return
    data = await state.get_data()
    action = data.get("action")
    await state.update_data({"user_id": user_id})
    await message.answer("Введите сумму (целое число):")
    await state.set_state("payout_waiting_amount")

@router.message(F.text, state="payout_waiting_amount")
async def payout_amount(message: types.Message, state):
    data = await state.get_data()
    user_id = data.get("user_id")
    action = data.get("action")
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную сумму (положительное число).")
        return

    issuer_id = message.from_user.id

    if action == "add":
        await add_payout(user_id, amount, issuer_id)
        await message.answer(f"Выплата {amount} успешно добавлена пользователю {user_id}.")
    elif action == "subtract":
        await subtract_payout(user_id, amount, issuer_id)
        await message.answer(f"Сумма {amount} успешно вычтена у пользователя {user_id}.")
    else:
        await message.answer("Неизвестное действие.")
    await state.clear()

@router.callback_query(F.data == "manage_bans")
async def manage_bans_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Забанить пользователя", callback_data="ban_user_start")],
        [InlineKeyboardButton(text="Разбанить пользователя", callback_data="unban_user_start")],
        [InlineKeyboardButton(text="Назад", callback_data="manage_users")],
    ])
    await callback.message.answer("Управление банами:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "ban_user_start")
async def ban_user_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ID пользователя для бана:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "ban_waiting_user_id")

@router.message(F.text, state="ban_waiting_user_id")
async def ban_user_waiting_user(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID.")
        return
    await state.update_data({"ban_user_id": user_id})
    await message.answer("Введите время блокировки в часах (целое число):")
    await state.set_state("ban_waiting_hours")

@router.message(F.text, state="ban_waiting_hours")
async def ban_user_waiting_hours(message: types.Message, state):
    try:
        hours = int(message.text)
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное число часов (>0).")
        return
    data = await state.get_data()
    user_id = data.get("ban_user_id")
    until = datetime.utcnow() + timedelta(hours=hours)
    await ban_user(user_id, until)
    await message.answer(f"Пользователь {user_id} заблокирован до {until.strftime('%Y-%m-%d %H:%M:%S UTC')}.")
    await state.clear()

@router.callback_query(F.data == "unban_user_start")
async def unban_user_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ID пользователя для разблокировки:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "unban_waiting_user_id")

@router.message(F.text, state="unban_waiting_user_id")
async def unban_user_waiting_user(message: types.Message, state):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Введите корректный числовой ID.")
        return
    await unban_user(user_id)
    await message.answer(f"Пользователь {user_id} разблокирован.")
    await state.clear()

# --- Посты (создание и отправка в канал) ---

from config import CHANNEL_IDS

@router.callback_query(F.data == "admin_posts")
async def admin_posts_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать новый пост", callback_data="create_post")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer("Панель постов:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "create_post")
async def create_post_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите текст поста для отправки пользователям:")
    await callback.answer()
    await callback.bot["fsm_storage"].set_state(callback.from_user.id, "post_waiting_text")

@router.message(F.text, state="post_waiting_text")
async def create_post_finish(message: types.Message, state):
    text = message.text
    # Добавляем в таблицу News
    async with SessionLocal() as session:
        from database import News
        new_post = News(content=text, sent=False)
        session.add(new_post)
        await session.commit()

    await message.answer("Пост сохранён и будет отправлен.")
    await state.clear()

    # Автоотправка в бот
    await send_news_to_all_users(text, message.bot)

async def send_news_to_all_users(text: str, bot):
    async with SessionLocal() as session:
        from database import User
        result = await session.execute(select(User))
        users = result.scalars().all()

    for user in users:
        try:
            await bot.send_message(user.user_id, text)
        except Exception:
            continue

@router.callback_query(F.data == "send_news_to_channel")
async def send_news_to_channel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    async with SessionLocal() as session:
        from database import News
        # Берём неотправленные новости
        result = await session.execute(select(News).where(News.sent == False))
        news_list = result.scalars().all()

        if not news_list:
            await callback.message.answer("Нет новых постов для отправки в канал.")
            await callback.answer()
            return

        for news in news_list:
            for ch_id in CHANNEL_IDS:
                try:
                    await callback.bot.send_message(ch_id, news.content)
                except Exception:
                    continue
            news.sent = True
        await session.commit()

    await callback.message.answer("Все новые посты отправлены в канал.")
    await callback.answer()
