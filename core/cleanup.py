# Стандартные библиотеки
import logging
from datetime import datetime, timedelta

# Сторонние библиотеки
import pytz
from sqlalchemy import and_, delete

# Локальные импорты
from database.database import Database
from database.models import SchedulerTask

class CleanupHandler:
    def __init__(self, db: Database):
        self._db = db

    async def cleanup_old_tasks(self):
        try:
            utc_tz = pytz.UTC
            cutoff_date = datetime.now(utc_tz) - timedelta(days=10)
            
            async for session in self._db.get_session():
                # Удаляем старые выполненные задачи
                delete_query = delete(SchedulerTask).where(
                    and_(
                        SchedulerTask.is_completed == True,
                        SchedulerTask.scheduled_time < cutoff_date
                    )
                )
                result = await session.execute(delete_query)
                await session.commit()
                
                deleted_count = result.rowcount
                logging.info(f"Удалено {deleted_count} старых выполненных задач")
        except Exception as e:
            logging.error(f"Ошибка при очистке старых задач: {e}")
            raise e 