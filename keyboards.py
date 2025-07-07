from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(role="user"):
    kb = [[KeyboardButton(text="📋 Подать заявку")], [KeyboardButton(text="📄 Моя анкета")]]
    if role in ["admin", "superadmin"]:
        kb.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

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
