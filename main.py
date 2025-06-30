import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, SUPER_ADMINS
from keyboards import main_menu, admin_panel_kb

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Состояния FSM
class ApplyForm(StatesGroup):
    waiting_for_application = State()

# Старт
@router.message(F.text == "/start")
async def start_cmd(message: Message):
    user_id = message.from_user.id
    role = "admin" if user_id in SUPER_ADMINS else "user"
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))

# Подать заявку
@router.message(F.text == "📋 Подать заявку")
async def apply_start(message: Message, state: FSMContext):
    await state.set_state(ApplyForm.waiting_for_application)
    await message.answer("Напиши текст своей заявки:")

@router.message(ApplyForm.waiting_for_application)
async def apply_process(message: Message, state: FSMContext):
    await message.answer("Заявка отправлена. Ожидай ответа.")
    await state.clear()

# Админ-панель
@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in SUPER_ADMINS:
        return await message.answer("Нет доступа.")
    await message.answer("Панель администратора:", reply_markup=admin_panel_kb)

# Кнопки админки
@router.callback_query(F.data == "view_stats")
async def view_stats(call: CallbackQuery):
    await call.message.edit_text(
        "👥 Пользователи: 42\n📬 Заявки: 12\n💸 Выплачено: 14900₽"
    )

@router.callback_query(F.data == "post_to_channels")
async def post_to_channels(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите текст для поста:")
    # Здесь можно использовать FSM для ожидания текста

# Автопостинг новостей
async def auto_post_news():
    while True:
        await asyncio.sleep(3600)
        # TODO: автопостинг логика

# Запуск бота
async def main():
    dp.include_router(router)
    asyncio.create_task(auto_post_news())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
