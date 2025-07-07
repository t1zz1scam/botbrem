import os
import logging
import asyncio
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Update
from aiogram.exceptions import TelegramRetryAfter

from database import init_db, engine, run_bigint_migration, ensure_banned_until_column
from profile import router as profile_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable is not set")

WEBHOOK_PATH = "/bot-webhook"

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL env variable is not set")

FULL_WEBHOOK_URL = WEBHOOK_URL + WEBHOOK_PATH

bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(profile_router)
dp.include_router(admin_router)

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    logger.info("Запуск миграции bigint...")
    await run_bigint_migration(engine)

    logger.info("Проверка и добавление поля banned_until, если необходимо...")
    await ensure_banned_until_column()

    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info(f"Установка webhook: {FULL_WEBHOOK_URL}")
    await bot.set_webhook(FULL_WEBHOOK_URL)

    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Удаляем webhook...")
    try:
        await bot.delete_webhook()
    except TelegramRetryAfter as e:
        logger.warning(f"Flood limit при удалении webhook: ждать {e.timeout} секунд")
        await asyncio.sleep(e.timeout)
        try:
            await bot.delete_webhook()
        except Exception as ex:
            logger.error(f"Ошибка при повторном удалении webhook: {ex}")

    logger.info("Закрываем хранилище FSM...")
    try:
        await storage.close()
    except Exception as e:
        logger.error(f"Ошибка при закрытии хранилища FSM: {e}")

    logger.info("Закрываем клиентскую сессию бота...")
    try:
        await bot.session.close()
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии бота: {e}")

    logger.info("Шатдаун завершен")


@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    try:
        json_data = await request.json()
        logger.info(f"Получен update: {json_data}")
        update = Update(**json_data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Ошибка при обработке update: {e}", exc_info=True)
        return Response(status_code=500)
    return Response(status_code=200)
