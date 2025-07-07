import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from config import BOT_TOKEN, DATABASE_URL

# Импорт роутеров (обработчиков) из файлов
from handlers.admin import router as admin_router
from handlers.profile import router as profile_router  # 👈 Добавлен profile.py

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация FastAPI-приложения
app = FastAPI()

# Создание бота с токеном и включенным HTML-парсингом
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# Диспетчер aiogram с памятью FSM-состояний (для состояний в profile/admin)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем все роутеры (обработчики команд и сообщений)
dp.include_router(admin_router)    # Хендлеры из admin.py
dp.include_router(profile_router) # Хендлеры из profile.py

# Инициализация движка SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True, future=True)


# Выполнение миграции bigint — при первом запуске
async def run_bigint_migration():
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='applications' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE applications ALTER COLUMN user_id TYPE BIGINT;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='applications' AND column_name='resolved_by' AND data_type='integer'
                ) THEN
                    ALTER TABLE applications ALTER COLUMN resolved_by TYPE BIGINT;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='payouts' AND column_name='user_id' AND data_type='integer'
                ) THEN
                    ALTER TABLE payouts ALTER COLUMN user_id TYPE BIGINT;
                END IF;
            END;
            $$;
        """))


# Автоматически запускается при запуске FastAPI (на Render и локально)
@app.on_event("startup")
async def on_startup():
    logging.info("Инициализация базы данных и миграций...")
    await run_bigint_migration()
    logging.info("✅ Миграции выполнены")
    logging.info("✅ Бот успешно запущен!")


# Вебхук для Telegram обновлений (обработка входящих сообщений)
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    try:
        await dp.feed_update(bot, update)  # Передаем update боту
    except Exception as e:
        logging.error(f"Ошибка при обработке update: {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)
    return JSONResponse(content={"status": "ok"})
