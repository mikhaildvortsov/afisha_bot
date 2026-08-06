import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from database import create_tables
from handlers import user_handlers, admin_handlers

# Загружаем переменные окружения
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")

async def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    if not TOKEN:
        logging.error("Токен не найден! Установите переменную BOT_TOKEN в файле .env")
        return

    # Инициализация бота
    bot = Bot(token=TOKEN)
    # Инициализация диспетчера
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    # Инициализация базы данных
    try:
        await create_tables()
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        return

    logging.info("Бот запущен...")
    
    # Запуск polling, пропуская старые апдейты
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка в работе бота: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
