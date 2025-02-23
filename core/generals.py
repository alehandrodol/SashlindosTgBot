import logging
import asyncio
from aiogram import Bot
from sqlalchemy import select
from database.database import Database
from database.models import Chat

async def send_status_message(bot: Bot, db: Database, message: str):
    """Отправляет сообщение о статусе бота во все активные чаты."""
    try:
        async for session in db.get_session():
            # Получаем все активные чаты
            query = select(Chat).where(Chat.is_active == True)
            result = await session.execute(query)
            active_chats = result.scalars().all()
            
            # Отправляем сообщение в каждый чат
            for chat in active_chats:
                try:
                    await bot.send_message(
                        chat_id=chat.chat_id,
                        text=message
                    )
                    await asyncio.sleep(0.1)  # Небольшая задержка между отправками
                except Exception as e:
                    logging.error(f"Ошибка при отправке статуса в чат {chat.chat_id}: {e}")
    except Exception as e:
        logging.error(f"Ошибка при отправке статуса: {e}") 