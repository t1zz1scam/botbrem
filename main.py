import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage  # FSM-хранилище в памяти

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from config import BOT_TOKEN, DATABASE_URL
from handlers.admin import router  # Импорт твоего админ-роутера

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем FastAPI-приложение
app = FastAPI()

# Создаём экземпляр бота
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# Создаём Dispatcher с FSM-хранилищем (обязательно в aiogram 3)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутер с обработчиками админки (один раз!)
dp.include_router(router)

# Создаём SQLAlchemy-движок для работы с базой данных
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Асинхронная миграция колонок user_id и resolved_by в BIGINT, если они ещё integer
async def run_bigint_migration():
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$
            BEGIN
                -- Преобразуем user_id и resolved_by в bigint, если они ещё integer
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

# Хук при запуске FastAPI (выполняем миграции)
@app.on_event("startup")
async def on_startup():
    logging.info("Инициализация базы данных и миграций...")
    await run_bigint_migration()
    logging.info("✅ Миграции выполнены")
    logging.info("✅ Бот успешно запущен!")

# Обработка входящих Webhook-запросов от Telegram
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    data = await request.json()  # Получаем данные update из Telegram
    update = Update(**data)      # Преобразуем в объект Update

    try:
        # Передаём обновление в aiogram для обработки
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        # Логируем и возвращаем ошибку, если что-то пошло не так
        logging.error(f"Ошибка при обработке update: {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

    return JSONResponse(content={"status": "ok"})
