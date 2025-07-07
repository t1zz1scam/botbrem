import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL от Render
SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID", "0"))
SUPER_ADMINS = list(map(int, os.getenv("SUPER_ADMINS", "").split(","))) if os.getenv("SUPER_ADMINS") else []
CHANNEL_IDS = list(map(int, os.getenv("CHANNEL_IDS", "").split(","))) if os.getenv("CHANNEL_IDS") else []
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
