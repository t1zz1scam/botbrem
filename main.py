import os
import logging
from fastapi import FastAPI
from aiohttp import web
from aiohttp_asgi import AiohttpAsgi
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from profile import router as profile_router  # твой FastAPI роутер
from keyboards import main_menu  # клавиатуры бота
from config import BOT_TOKEN, SUPER_ADMINS  # токен и админы

logging.basicConfig(level=logging.INFO)

WEBHOOK_PATH = "/bot-webhook"
WEBHOOK_URL = f"https://botbrem.onrender.com{WEBHOOK_PATH}"  # <- ЗАМЕНИТЕ НА СВОЙ ДОМЕН!

# FastAPI приложение
app = FastAPI()
app.include_router(profile_router)

# Telegram bot (aiohttp + aiogram)
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    role = "admin" if message.from_user.id in SUPER_ADMINS else "user"
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))

async def handle_webhook(request: web.Request):
    data = await request.json()
    update = types.Update.parse_obj(data)
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app_):
    logging.info(f"Setting webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app_):
    logging.info("Deleting webhook and closing bot session")
    await bot.delete_webhook()
    await bot.session.close()

# Создаем aiohttp приложение
aiohttp_app = web.Application()
aiohttp_app.router.add_post(WEBHOOK_PATH, handle_webhook)
aiohttp_app.on_startup.append(on_startup)
aiohttp_app.on_cleanup.append(on_shutdown)

# Оборачиваем aiohttp в ASGI
asgi_aiohttp = AiohttpAsgi(aiohttp_app)

# Монтируем aiohttp приложение в FastAPI на пути /bot-webhook
app.mount(WEBHOOK_PATH, asgi_aiohttp)
