from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(role="user"):
    kb = [[KeyboardButton("📋 Подать заявку")], [KeyboardButton("📄 Моя анкета")]]
    if role in ["admin", "superadmin"]:
        kb.append([KeyboardButton("🛠 Админ-панель")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📬 Заявки", callback_data="view_applications")],
    [InlineKeyboardButton(text="💸 Выплаты", callback_data="manage_payouts")],
    [InlineKeyboardButton(text="📰 Пост в канал", callback_data="post_to_channels")],
    [InlineKeyboardButton(text="📊 Статистика", callback_data="view_stats")],
])
