import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

# Импорты из твоего проекта: базы данных и роутеры с обработчиками
from database import (
    init_db,                   # Функция инициализации базы данных (создание таблиц)
    run_bigint_migration,      # Функция миграции id к BIGINT (если надо)
    ensure_banned_until_column,# Добавление колонки banned_until, если отсутствует
    ensure_user_rank_rename,   # Переименование колонки rank → user_rank
    engine,                    # Экземпляр движка SQLAlchemy
    create_user_if_not_exists, # Создать пользователя, если его нет в БД
)
from handlers import router as handlers_router  # Объединённый роутер из папки handlers
from config import BOT_TOKEN, WEBHOOK_URL, SUPERADMIN_ID

# Загружаем переменные окружения из .env файла
load_dotenv()

# Создаем объект бота с токеном и настройками (HTML формат сообщений)
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

# Диспетчер для обработки событий и маршрутизации команд/сообщений
dp = Dispatcher()

# Регистрируем в диспетчере все роутеры из handlers (все обработчики)
dp.include_router(handlers_router)

# Настраиваем логирование на уровень INFO (выводит инфо-сообщения в консоль)
logging.basicConfig(level=logging.INFO)

# Создаем FastAPI приложение (ASGI)
app = FastAPI()

# --- Обработчик события старта сервера (FastAPI) ---
@app.on_event("startup")
async def on_startup():
    logging.info("▶ Инициализация базы данных и миграций...")

    # Создаем таблицы в базе, если их нет
    await init_db()
    # Запускаем миграцию типа bigint для id (если нужно)
    await run_bigint_migration(engine)
    # Убедимся, что колонка banned_until есть
    await ensure_banned_until_column(engine)
    # Переименовываем колонку rank в user_rank, если нужно
    await ensure_user_rank_rename(engine)

    # Регистрируем webhook у Telegram на указанный URL
    await bot.set_webhook(WEBHOOK_URL, secret_token=None)

    # Устанавливаем команды /start и /help для удобства пользователей
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ])

    # Создаем суперадмина в базе, если задан в конфиге
    if SUPERADMIN_ID:
        await create_user_if_not_exists(SUPERADMIN_ID)
        logging.info(f"👑 Суперадмин {SUPERADMIN_ID} зарегистрирован")

    logging.info("✅ Бот успешно запущен!")

# --- Обработчик события завершения работы сервера (FastAPI) ---
@app.on_event("shutdown")
async def on_shutdown():
    # Закрываем сессию бота (очищаем ресурсы)
    await bot.session.close()

# --- Webhook endpoint, куда Телега шлёт обновления ---
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    # Получаем JSON с обновлением от Telegram
    update = await request.json()
    # Передаем обновление в диспетчер aiogram для обработки
    await dp.feed_update(bot, update, request)
    # Возвращаем простой ответ с OK
    return JSONResponse(content={"status": "ok"})

# --- Точка входа при запуске скрипта напрямую ---
if __name__ == "__main__":
    import uvicorn
    # Запускаем ASGI приложение с помощью uvicorn
    # main:app — говорит, что в модуле main лежит объект app (FastAPI)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,  # Автоматическая перезагрузка при изменениях кода (для dev)
    )
