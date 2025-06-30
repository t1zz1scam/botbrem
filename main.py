import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, SUPER_ADMINS
from keyboards import main_menu, admin_panel_kb

logging.basicConfig(level=logging.DEBUG)  # Для подробных логов

PORT = int(os.getenv("PORT", 8000))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://botbrem.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

class ApplyForm(StatesGroup):
    waiting_for_application = State()

@router.message(F.command == "start")
async def start_cmd(message: Message):
    logging.info(f"Получена команда /start от {message.from_user.id}")
    role = "admin" if message.from_user.id in SUPER_ADMINS else "user"
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))

@router.message(F.text == "📋 Подать заявку")
async def apply_start(message: Message, state: FSMContext):
    await state.set_state(ApplyForm.waiting_for_application)
    await message.answer("Напиши текст своей заявки:")

@router.message(ApplyForm.waiting_for_application)
async def apply_process(message: Message, state: FSMContext):
    await message.answer("Заявка отправлена. Ожидай ответа.")
    await state.clear()

@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in SUPER_ADMINS:
        return await message.answer("Нет доступа.")
    await message.answer("Панель администратора:", reply_markup=admin_panel_kb)

@router.callback_query(F.data == "view_stats")
async def view_stats(call: CallbackQuery):
    await call.message.edit_text(
        "👥 Пользователи: 42\n📬 Заявки: 12\n💸 Выплачено: 14900₽"
    )

@router.callback_query(F.data == "post_to_channels")
async def post_to_channels(call: CallbackQuery):
    await call.message.answer("Введите текст для поста:")

# Простой эхо-обработчик для проверки, что бот работает
@router.message()
async def echo_all(message: Message):
    logging.info(f"Эхо: получено сообщение: {message.text}")
    await message.answer(f"Вы написали: {message.text}")

dp.include_router(router)

async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        logging.info(f"Webhook Update: {data}")
        update = types.Update.parse_obj(data)
        await dp.feed_update(bot, update)  # bot — обязательный первый аргумент!
    except Exception as e:
        logging.error(f"Ошибка при обработке webhook: {e}")
    return web.Response()


async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
