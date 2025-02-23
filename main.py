import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import load_config
from handlers import registration, daily, stats
from database import DatabaseMiddleware, Database, DatabaseConfig
from core.scheduler import Scheduler
from core.middleware import SchedulerMiddleware

# Включаем логирование
logging.basicConfig(level=logging.INFO)

config_path = ".env"

async def main():
    # Загружаем конфиг
    config = load_config(config_path)
    
    # Инициализируем бота и диспетчер
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()

    # Инициализируем базу данных
    db_config = DatabaseConfig(config)
    db = Database(db_config)
    
    # Инициализируем и настраиваем планировщик
    scheduler = Scheduler(bot, db)
    
    # Добавляем middleware
    dp.update.middleware(DatabaseMiddleware(db))
    dp.update.middleware(SchedulerMiddleware(scheduler))
    
    # Проверяем пропущенные сообщения и настраиваем задачи
    async for session in db.get_session():
        await scheduler.check_missed_dailies(session)
        await scheduler.setup_jobs(session)

    # Регистрируем роутеры
    dp.include_router(registration.router)
    dp.include_router(daily.router)
    dp.include_router(stats.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=[
            "message",
            "chat_member",
            "callback_query"
        ])
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 