from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(role="user"):
    kb = [[KeyboardButton("📋 Подать заявку")], [KeyboardButton("📄 Моя анкета")]]
    if role in ["admin", "superadmin"]:
        kb.append([KeyboardButton("🛠 Админ-панель")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("📬 Заявки", callback_data="view_applications")],
    [InlineKeyboardButton("💸 Выплаты", callback_data="manage_payouts")],
    [InlineKeyboardButton("📰 Пост в канал", callback_data="post_to_channels")],
    [InlineKeyboardButton("📊 Статистика", callback_data="view_stats")],
])