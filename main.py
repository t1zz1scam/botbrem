import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Конфиги
from config import BOT_TOKEN, DATABASE_URL
from handlers import router as handlers_router  # Импортируем единый router с админом и профилем

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI-приложение
app = FastAPI()

# Создаем экземпляр бота
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# Dispatcher без передачи бота напрямую — правильно для aiogram 3.x
dp = Dispatcher()

# Подключаем единый router, где уже собраны все подроутеры (admin, profile и др.)
# 💡 Важно: router подключается только один раз, чтобы избежать RuntimeError
dp.include_router(handlers_router)

# Создаем подключение к базе данных
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Миграции: Преобразование колонок integer -> bigint, добавление колонок, переименование и т.п.
async def run_migrations():
    """
    Выполняет все необходимые миграции для базы данных:
    - Преобразование колонок user_id, resolved_by, issued_by с integer на bigint, если нужно
    - Добавление колонки banned_until, если её нет
    - Переименование колонки rank в user_rank, если есть старая колонка rank
    - Добавление колонки user_rank, если её нет
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
        DO $$
        BEGIN
            -- bigint миграции
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

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='payouts' AND column_name='issued_by' AND data_type='integer'
            ) THEN
                ALTER TABLE payouts ALTER COLUMN issued_by TYPE BIGINT;
            END IF;

            -- Добавление колонки banned_until, если её нет
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='banned_until'
            ) THEN
                ALTER TABLE users ADD COLUMN banned_until TIMESTAMP NULL;
            END IF;

            -- Переименование колонки rank в user_rank, если есть старая
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='rank'
            ) THEN
                ALTER TABLE users RENAME COLUMN rank TO user_rank;
            END IF;

            -- Добавление колонки user_rank, если её нет и нет колонки rank
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='user_rank'
            ) THEN
                ALTER TABLE users ADD COLUMN user_rank VARCHAR(255) NULL;
            END IF;

        END;
        $$;
        """))

# Запускается при старте FastAPI
@app.on_event("startup")
async def on_startup():
    logging.info("📦 Выполняем миграции...")
    await run_migrations()
    logging.info("✅ Миграции выполнены")
    logging.info("🚀 Бот готов к приему запросов!")

# Webhook для Telegram
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    try:
        # Логируем полученные данные
        data = await request.json()
        logger.info(f"Received update: {data}")  # Логируем входящее обновление

        # Передаем данные в диспетчер
        update = Update(**data)
        await dp.feed_update(bot, update)
        logger.info(f"Update processed: {data}")  # Логируем успешную обработку

    except Exception as e:
        # Логируем ошибки
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

    return JSONResponse(content={"status": "ok"})

# Проверка вебхука (для диагностики)
@app.get("/check-webhook")
async def check_webhook():
    try:
        # Проверим текущий статус вебхука
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")
        return {"status": "ok", "webhook_info": webhook_info}
    except Exception as e:
        logger.error(f"Error checking webhook: {e}")
        return {"status": "error", "detail": str(e)}
