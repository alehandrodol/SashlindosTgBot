import pytz
import random
import logging

from aiogram import Bot
from datetime import datetime
from sqlalchemy import select, and_

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .daily import DailyHandler
from .cleanup import CleanupHandler
from database.database import Database
from database.models import Chat, SchedulerTask, TaskType

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class Scheduler:
    _bot: Bot
    _db: Database 
    _scheduler: AsyncIOScheduler
    _daily_handler: DailyHandler
    _cleanup_handler: CleanupHandler

    def __init__(self, bot: Bot, db: Database):
        self._bot = bot
        self._db = db
        self._scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
        self._daily_handler = DailyHandler(bot, db)
        self._cleanup_handler = CleanupHandler(db)
    
    async def schedule_daily_master(self, chat_id: int):
        """Планирует следующее ежедневное сообщение для поиска пидоров в чате."""
        try:
            # Генерируем случайное время
            hour = random.randint(9, 21)
            minute = random.randint(0, 59)
            
            # Вычисляем следующее время
            now = datetime.now(MOSCOW_TZ)
            next_time = now.replace(
                day=now.day + 1,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            
            async for session in self._db.get_session():
                # Создаем новую задачу
                new_task = SchedulerTask(
                    chat_id=chat_id,
                    task_type=TaskType.DAILY_MESSAGE,
                    scheduled_time=next_time,
                    is_completed=False
                )
                session.add(new_task)
                await session.commit()
                
                # Переиспользуем существующий метод для планирования
                await self._schedule_task(new_task)
            
            logging.info(f"Запланировано сообщение для чата {chat_id} на {next_time}")
            
        except Exception as e:
            logging.error(f"Ошибка при планировании следующего сообщения для чата {chat_id}: {e}")
    
    async def check_missed_dailies(self, session):
        """Проверяет и обрабатывает пропущенные ежедневные сообщения."""
        try:
            now = datetime.now(MOSCOW_TZ)
            
            # Получаем все невыполненные задачи, время которых уже прошло
            query = select(SchedulerTask).where(
                and_(
                    SchedulerTask.is_completed == False,
                    SchedulerTask.scheduled_time <= now,
                    SchedulerTask.task_type == TaskType.DAILY_MESSAGE
                )
            )
            
            result = await session.execute(query)
            missed_tasks: list[SchedulerTask] = result.scalars().all()
            
            for task in missed_tasks:
                await self._bot.send_message(
                    task.chat_id,
                    "Извините, было пропущено запланированное сообщение из-за технических проблем! 🤖"
                )
                
                # Помечаем задачу как выполненную
                task.is_completed = True
                
                # Планируем следующее сообщение
                await self.schedule_daily_master(task.chat_id)
                
            await session.commit()
            
            if missed_tasks:
                logging.info(f"Обработано {len(missed_tasks)} пропущенных сообщений")
                
        except Exception as e:
            logging.error(f"Ошибка при проверке пропущенных сообщений: {e}")

    async def _restore_pending_tasks(self, session) -> int:
        """Восстанавливает существующие невыполненные задачи."""
        now = datetime.now(MOSCOW_TZ)
        task_query = select(SchedulerTask).where(
            and_(
                SchedulerTask.is_completed == False,
                SchedulerTask.scheduled_time > now,
                SchedulerTask.task_type == TaskType.DAILY_MESSAGE
            )
        )
        result = await session.execute(task_query)
        pending_tasks: list[SchedulerTask] = result.scalars().all()
        
        for task in pending_tasks:
            await self._schedule_task(task)
            
        return len(pending_tasks)

    async def _schedule_task(self, task: SchedulerTask):
        """Планирует отдельную задачу в планировщике."""
        scheduled_time = task.scheduled_time.astimezone(MOSCOW_TZ)
        self._scheduler.add_job(
            self._daily_handler.send_daily_message,
            trigger=CronTrigger(
                year=scheduled_time.year,
                month=scheduled_time.month,
                day=scheduled_time.day,
                hour=scheduled_time.hour,
                minute=scheduled_time.minute
            ),
            args=[task.chat_id, task.id],
            id=f'daily_message_{task.chat_id}',
            replace_existing=True,
            kwargs={'scheduler': self}
        )
        logging.info(f"Восстановлена задача {task.id} для чата {task.chat_id} на {scheduled_time}")

    async def _setup_active_chats(self, session):
        """Планирует задачи для активных чатов без существующих задач."""
        # Создаем подзапрос для активных задач
        active_tasks = (
            select(SchedulerTask)
            .where(
                and_(
                    SchedulerTask.is_completed == False,
                    SchedulerTask.task_type == TaskType.DAILY_MESSAGE
                )
            )
            .subquery()
        )

        # Основной запрос с LEFT JOIN
        query = (
            select(Chat, active_tasks)
            .outerjoin(
                active_tasks,
                and_(
                    Chat.chat_id == active_tasks.c.chat_id,
                )
            )
            .where(
                and_(
                    Chat.is_active == True,
                    active_tasks.c.id == None  # выбираем только чаты без активных задач
                )
            )
        )
        
        result = await session.execute(query)
        chats_without_tasks = result.scalars().all()
        
        for chat in chats_without_tasks:
            await self.schedule_daily_master(chat.chat_id)
            logging.info(f"Создана новая задача для чата {chat.chat_id}")

    def _setup_cleanup_job(self):
        """Настраивает ежедневную задачу очистки."""
        self._scheduler.add_job(
            self._cleanup_handler.cleanup_old_tasks,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_old_tasks',
            replace_existing=True
        )

    async def setup_jobs(self, session):
        """Основная функция настройки планировщика."""
        try:
            # 1. Восстанавливаем существующие задачи
            restored_count = await self._restore_pending_tasks(session)
            
            # 2. Планируем новые задачи для активных чатов
            await self._setup_active_chats(session)
            
            # 3. Настраиваем задачу очистки
            self._setup_cleanup_job()
            
            # Запускаем планировщик
            self._scheduler.start()
            logging.info(f"Планировщик успешно запущен. Восстановлено {restored_count} задач")
            
        except Exception as e:
            logging.error(f"Ошибка при настройке планировщика: {e}")

    async def setup_chat_job(self, chat_id: int):
        """Настройка ежедневной задачи для конкретного чата"""
        try:
            await self.schedule_daily_master(chat_id)
            logging.info(f"Настроена ежедневная задача для чата {chat_id}")
        except Exception as e:
            logging.error(f"Ошибка при настройке задачи для чата {chat_id}: {e}")

    def get_scheduled_jobs(self):
        """Получить все запланированные задачи"""
        jobs = self._scheduler.get_jobs()
        scheduled_jobs = []
        
        for job in jobs:
            scheduled_jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time,
                'args': job.args,
                'trigger': str(job.trigger)
            })
            
        return scheduled_jobs
