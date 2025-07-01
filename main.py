import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.utils.executor import start_webhook
from database import init_db
from profile import router as profile_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/bot-webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем роутеры
dp.include_router(profile_router)
dp.include_router(admin_router)

async def on_startup():
    logging.info("Инициализация базы данных...")
    await init_db()

    logging.info(f"Установка webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Команды бота установлены")

async def on_shutdown():
    logging.info("Удаляем webhook...")
    await bot.delete_webhook()
    await storage.close()
    await storage.wait_closed()
    logging.info("Шатдаун завершен")

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
