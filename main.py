import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from dotenv import load_dotenv

from database import init_db, run_bigint_migration, ensure_banned_until_column, ensure_user_rank_rename, engine, create_user_if_not_exists
from handlers import router as handlers_router
from config import BOT_TOKEN, WEBHOOK_URL, SUPERADMIN_ID

load_dotenv()

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
dp.include_router(handlers_router)

logging.basicConfig(level=logging.INFO)

async def on_startup():
    logging.info("▶ Инициализация базы данных и миграций...")
    await init_db()
    await run_bigint_migration(engine)
    await ensure_banned_until_column(engine)
    await ensure_user_rank_rename(engine)

    await bot.set_webhook(WEBHOOK_URL, secret_token=None)

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ])

    if SUPERADMIN_ID:
        await create_user_if_not_exists(SUPERADMIN_ID)
        logging.info(f"👑 Суперадмин {SUPERADMIN_ID} зарегистрирован")

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
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=None).register(app, path="/bot-webhook")
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
