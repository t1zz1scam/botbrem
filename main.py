import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from database import (
    init_db, run_bigint_migration, ensure_banned_until_column,
    create_user_if_not_exists
)
from handlers import router as handlers_router  # <-- твой router с хендлерами

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/bot-webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
dp.include_router(handlers_router)

logging.basicConfig(level=logging.INFO)

async def on_startup():
    logging.info("▶ Инициализация базы данных и миграций...")
    await init_db()
    await run_bigint_migration(engine=bot.session.engine)
    await ensure_banned_until_column(engine=bot.session.engine)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

    # Установка команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ])

    # Убедиться, что superadmin есть в БД
    superadmin_id = int(os.getenv("SUPER_ADMIN_ID", 0))
    if superadmin_id:
        await create_user_if_not_exists(superadmin_id)
        logging.info(f"👑 Суперадмин {superadmin_id} зарегистрирован")

    logging.info("✅ Бот успешно запущен!")

async def bot_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, update, request)
    return web.Response()

async def on_shutdown(app):
    await bot.session.close()

def create_app():
    app = web.Application()
    app.on_startup.append(lambda _: on_startup())
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)

    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
