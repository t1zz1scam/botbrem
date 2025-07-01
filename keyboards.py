from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(role="user"):
    kb = [[KeyboardButton(text="📋 Подать заявку")], [KeyboardButton(text="📄 Моя анкета")]]
    if role in ["admin", "superadmin"]:
        kb.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📬 Заявки", callback_data="view_applications")],
    [InlineKeyboardButton(text="💸 Выплаты", callback_data="manage_payouts")],
    [InlineKeyboardButton(text="📰 Пост в канал", callback_data="post_to_channels")],
    [InlineKeyboardButton(text="📊 Статистика", callback_data="view_stats")],
])
