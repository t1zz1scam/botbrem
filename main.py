import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

# Импорты из проекта: база и роутеры
from database import (
    init_db,                   # Инициализация базы (создание таблиц)
    run_bigint_migration,      # Миграция id в bigint
    ensure_banned_until_column,# Добавление колонки banned_until, если отсутствует
    ensure_user_rank_column,   # Новая функция для колонки user_rank
    engine,                    # Движок SQLAlchemy
    create_user_if_not_exists, # Создание пользователя при отсутствии
)
from handlers import router as handlers_router  # Объединённый роутер обработчиков
from config import BOT_TOKEN, WEBHOOK_URL, SUPERADMIN_ID

# Загружаем переменные из .env
load_dotenv()

# Создаем бота с HTML разметкой сообщений
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

# Диспетчер для обработки событий
dp = Dispatcher()

# Регистрируем роутеры из папки handlers
dp.include_router(handlers_router)

# Логируем INFO уровень
logging.basicConfig(level=logging.INFO)

# Создаем FastAPI приложение
app = FastAPI()

# --- При старте приложения ---
@app.on_event("startup")
async def on_startup():
    logging.info("▶ Инициализация базы данных и миграций...")

    # Создаем таблицы в базе, если отсутствуют
    await init_db()
    # Миграция id с integer на bigint (если требуется)
    await run_bigint_migration(engine)
    # Проверяем и добавляем колонку banned_until
    await ensure_banned_until_column(engine)
    # Проверяем и создаем/переименовываем колонку user_rank
    await ensure_user_rank_column(engine)

    # Регистрируем webhook у Telegram
    await bot.set_webhook(WEBHOOK_URL, secret_token=None)

    # Устанавливаем команды для удобства пользователей
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ])

    # Создаем суперадмина, если задан
    if SUPERADMIN_ID:
        await create_user_if_not_exists(SUPERADMIN_ID)
        logging.info(f"👑 Суперадмин {SUPERADMIN_ID} зарегистрирован")

    logging.info("✅ Бот успешно запущен!")

# --- При остановке приложения ---
@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()

# --- Обработка webhook запросов от Telegram ---
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    update = await request.json()
    await dp.feed_update(bot=bot, update=update)
    return JSONResponse(content={"status": "ok"})

# --- Точка запуска с uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
