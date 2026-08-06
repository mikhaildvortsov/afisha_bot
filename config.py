import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
ADMIN_ID = int(os.getenv("ADMIN_ID", ADMIN_IDS[0] if ADMIN_IDS else 0))
