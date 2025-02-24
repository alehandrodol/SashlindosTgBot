import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import load_config
from handlers import registration, daily, stats, admin, entertainment, help
from database import DatabaseMiddleware, Database, DatabaseConfig
from core.scheduler import Scheduler
from core.middleware import SchedulerMiddleware, VKMiddleware
from core.generals import send_status_message

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

    # Инициализируем VK API
    vk_middleware = VKMiddleware(config.vk.token)
    
    # Добавляем middleware
    dp.update.middleware(DatabaseMiddleware(db))
    dp.update.middleware(SchedulerMiddleware(scheduler))
    dp.update.middleware(vk_middleware)
    # Проверяем пропущенные сообщения и настраиваем задачи
    async for session in db.get_session():
        await scheduler.check_missed_dailies(session)
        await scheduler.setup_jobs(session)

    # Регистрируем роутеры
    dp.include_router(registration.router)
    dp.include_router(daily.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)
    dp.include_router(entertainment.router)
    dp.include_router(help.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        # Отправляем сообщение о запуске
        await send_status_message(
            bot, 
            db, 
            "🟢 Бот запущен и готов к работе!"
        )

        await dp.start_polling(bot, allowed_updates=[
            "message",
            "chat_member",
            "my_chat_member",
            "callback_query"
        ])
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise e
    finally:
        # Отправляем сообщение о выключении
        await send_status_message(
            bot, 
            db, 
            "🔴 Бот выключается на техническое обслуживание..."
        )
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 