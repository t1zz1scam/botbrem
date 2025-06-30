import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from config import BOT_TOKEN, SUPER_ADMINS
from keyboards import main_menu, admin_panel_kb

logging.basicConfig(level=logging.INFO)

PORT = int(os.getenv("PORT", 8000))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://botbrem.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

@router.message(F.text == "/start")
async def start_cmd(message: types.Message):
    logging.info(f"Получена команда /start от {message.from_user.id}")
    role = "admin" if message.from_user.id in SUPER_ADMINS else "user"
    logging.info(f"Роль пользователя: {role}")
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))
    logging.info("Ответ на /start отправлен")

# Эхо-обработчик для проверки, что бот отвечает на любое сообщение
@router.message()
async def echo_all(message: types.Message):
    logging.info(f"Эхо: получено сообщение: {message.text}")
    await message.answer(f"Вы написали: {message.text}")

dp.include_router(router)

async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        logging.info(f"Webhook Update: {data}")
        update = types.Update.parse_obj(data)  # <- вот тут изменение
        logging.info("До вызова feed_update")
        await dp.feed_update(bot, update)
        logging.info("После вызова feed_update")
    except Exception as e:
        logging.error(f"Ошибка при обработке webhook: {e}")
    return web.Response()

async def on_startup(app):
    logging.info(f"Установка webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    logging.info("Удаление webhook и закрытие сессии бота")
    await bot.delete_webhook()
    await bot.session.close()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    logging.info(f"Запуск приложения на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
