from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(role="user"):
    kb = [[KeyboardButton(text="📋 Подать заявку")], [KeyboardButton(text="📄 Моя анкета")]]
    if role in ["admin", "superadmin"]:
        kb.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📬 Заявки", callback_data="view_applications")],
    [InlineKeyboardButton(text="👥 Пользователи", callback_data="view_users")],
    [InlineKeyboardButton(text="✏ Управление пользователями", callback_data="manage_users")],
    [InlineKeyboardButton(text="📢 Посты", callback_data="admin_posts")],
])
