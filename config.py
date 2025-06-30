import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL от Render
SUPER_ADMINS = list(map(int, os.getenv("SUPER_ADMINS", "").split(",")))
CHANNEL_IDS = list(map(int, os.getenv("CHANNEL_IDS","").split(",")))