import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Update
from database import init_db
from profile import router as profile_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/bot-webhook"

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL environment variable is not set")
WEBHOOK_URL += WEBHOOK_PATH

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(profile_router)
dp.include_router(admin_router)

app = FastAPI()

@app.on_event("startup")
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

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("Удаляем webhook...")
    await bot.delete_webhook()
    await storage.close()
    await storage.wait_closed()
    logging.info("Шатдаун завершен")

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    json_data = await request.json()
    update = Update(**json_data)
    await dp.process_update(update)
    return Response(status_code=200)
