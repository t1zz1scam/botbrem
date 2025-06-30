import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUPER_ADMINS
from keyboards import main_menu, admin_panel_kb

# Логи
logging.basicConfig(level=logging.INFO)

# Переменные окружения
PORT = int(os.getenv("PORT", 8000))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://botbrem.onrender.com{WEBHOOK_PATH}"

# Инициализация
router = Router()
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

# Состояния FSM
class ApplyForm(StatesGroup):
    waiting_for_application = State()

# Хендлеры
@router.message(F.text == "/start")
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    role = "admin" if user_id in SUPER_ADMINS else "user"
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))

@router.message(F.text == "📋 Подать заявку")
async def apply_start(message: types.Message, state: FSMContext):
    await state.set_state(ApplyForm.waiting_for_application)
    await message.answer("Напиши текст своей заявки:")

@router.message(ApplyForm.waiting_for_application)
async def apply_process(message: types.Message, state: FSMContext):
    await message.answer("Заявка отправлена. Ожидай ответа.")
    await state.clear()

@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in SUPER_ADMINS:
        return await message.answer("Нет доступа.")
    await message.answer("Панель администратора:", reply_markup=admin_panel_kb)

@router.callback_query(F.data == "view_stats")
async def view_stats(call: types.CallbackQuery):
    await call.message.edit_text("👥 Пользователи: 42\n📬 Заявки: 12\n💸 Выплачено: 14900₽")

@router.callback_query(F.data == "post_to_channels")
async def post_to_channels(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Введите текст для поста:")

# Автозадача
async def auto_post_news():
    while True:
        logging.info("Автопостинг — заглушка работает.")
        await asyncio.sleep(3600)

# Webhook обработчик
async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        logging.info(f"Webhook Update: {data}")
        update = types.Update(**data)
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logging.error(f"Ошибка при обработке webhook: {e}")
    return web.Response()

# AIOHTTP приложение
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook установлен: {WEBHOOK_URL}")
    app['auto_post_task'] = asyncio.create_task(auto_post_news())

async def on_shutdown(app):
    await bot.delete_webhook()
    app['auto_post_task'].cancel()
    try:
        await app['auto_post_task']
    except asyncio.CancelledError:
        pass
    await bot.session.close()
    logging.info("Бот выключен и webhook удалён.")

app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
