import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Суперадмины задаются только через окружение и не могут быть удалены из бота.
SUPER_ADMIN_IDS = [int(i.strip()) for i in os.getenv("SUPER_ADMIN_IDS", "").split(",") if i.strip()]

# Обычные админы, заданные в окружении. Остальные хранятся в БД и правятся из бота.
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
