import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Конфиги
from config import BOT_TOKEN, DATABASE_URL
from handlers.admin import router as admin_router
from handlers.profile import router as profile_router  # Профильный router

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# FastAPI-приложение
app = FastAPI()

# Создаем экземпляр бота
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# Dispatcher без передачи бота напрямую — правильно для aiogram 3.x
dp = Dispatcher()

# Подключаем один и тот же router только один раз
# 💡 Важно: каждый router можно подключать только один раз!
dp.include_router(admin_router)     # Админка
dp.include_router(profile_router)  # Профиль и заявки

# Создаем подключение к базе данных
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Миграция колонок с integer → bigint, если нужно
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

# Запускается при старте FastAPI
@app.on_event("startup")
async def on_startup():
    logging.info("📦 Выполняем миграции...")
    await run_bigint_migration()
    logging.info("✅ Миграции выполнены")
    logging.info("🚀 Бот готов к приему запросов!")

# Webhook для Telegram
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)  # ⬅ правильно передаем bot
    except Exception as e:
        logging.error(f"❌ Ошибка в webhook: {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

    return JSONResponse(content={"status": "ok"})
