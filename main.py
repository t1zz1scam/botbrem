import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUPER_ADMINS
from keyboards import main_menu
from profile import router as profile_router  # твой aiogram Router

logging.basicConfig(level=logging.INFO)

PORT = int(os.getenv("PORT", 8000))
WEBHOOK_PATH = "/bot-webhook"
WEBHOOK_URL = f"https://botbrem.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрируем твой router в Dispatcher
dp.include_router(profile_router)

app = FastAPI()

# Твой хендлер команды /start
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    logging.info(f"Получена команда /start от {message.from_user.id}")
    role = "admin" if message.from_user.id in SUPER_ADMINS else "user"
    await message.answer("Добро пожаловать!", reply_markup=main_menu(role))
    logging.info("Ответ на /start отправлен")

# Регистрация start_cmd в Dispatcher
dp.include_router(dp.router)  # Это может быть лишним, если dp.router уже содержит start_cmd
# Можно просто так:
# dp.message.register(start_cmd, F.text == "/start")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logging.info(f"Webhook Update: {data}")
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Ошибка при обработке webhook: {e}")
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)
    return JSONResponse(content={"ok": True})

@app.on_event("startup")
async def on_startup():
    logging.info(f"Установка webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("Удаление webhook и закрытие сессии бота")
    await bot.delete_webhook()
    await bot.session.close()

if __name__ == "__main__":
    import uvicorn

    logging.info(f"Запуск приложения на порту {PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")
