import logging

from aiogram import Bot
from sqlalchemy import select
from database.database import Database
from database.models import SchedulerTask, Chat
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class DailyHandler:
    _bot: Bot
    _db: Database

    def __init__(self, bot: Bot, db: Database):
        self._bot = bot
        self._db = db

    async def send_daily_message(self, chat_id: int, task_id: int, scheduler=None):
        try:
            # Проверяем активность чата
            async for session in self._db.get_session():
                chat = await session.execute(
                    select(Chat).where(Chat.chat_id == chat_id)
                )
                chat = chat.scalar_one_or_none()
                
                if not chat or not chat.is_active:
                    logging.info(f"Пропуск отправки сообщения в неактивный чат {chat_id}")
                    return

            message_text = "Запустить локатор пидоров! 📡"
            
            # Создаем клавиатуру с кнопкой
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Я первый! 🚀",
                            callback_data=f"daily_first_{task_id}"
                        )
                    ]
                ]
            )
            
            await self._bot.send_message(
                chat_id, 
                message_text, 
                reply_markup=keyboard
            )
            
            # Помечаем задачу как выполненную по id
            async for session in self._db.get_session():
                query = select(SchedulerTask).where(SchedulerTask.id == task_id)
                result = await session.execute(query)
                task: SchedulerTask | None = result.scalar_one_or_none()
                
                if task:
                    task.is_completed = True
                    await session.commit()
            
            logging.info(f"Отправлено ежедневное сообщение в чат {chat_id}")
            
            # Планируем следующую задачу через переданный scheduler
            if scheduler:
                await scheduler.schedule_daily_master(chat_id)
            
        except Exception as e:
            logging.error(f"Ошибка при отправке ежедневного сообщения в чат {chat_id}: {e}")
            raise e 
