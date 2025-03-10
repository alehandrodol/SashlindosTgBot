# Стандартные библиотеки
import logging
import pytz
from datetime import datetime

# Сторонние библиотеки
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, and_, update, func, or_, case
from aiogram.utils.markdown import hbold
from core.vk_handler import VKHandler

# Локальные импорты
from database.models import SchedulerTask, TaskType, User, UserStats

router = Router()
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

@router.message(Command("daily_status"))
async def cmd_daily_status(message: Message, session):
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        # Получаем текущую дату в МСК
        utc_tz = pytz.UTC
        now = datetime.now(utc_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ищем выполненную задачу на сегодня
        query = select(SchedulerTask).where(
            and_(
                SchedulerTask.chat_id == message.chat.id,
                SchedulerTask.task_type == TaskType.DAILY_MESSAGE,
                SchedulerTask.scheduled_time >= today_start,
                SchedulerTask.scheduled_time <= now,
                SchedulerTask.is_completed == True
            )
        )
        
        result = await session.execute(query)
        completed_task = result.scalar_one_or_none()
        
        if completed_task:
            completed_time = completed_task.scheduled_time.astimezone(utc_tz)
            await message.answer(
                f"Локатор пидоров уже был запущен сегодня в {completed_time.astimezone(MOSCOW_TZ).strftime('%H:%M')} 🎉"
            )
        else:
            # Проверяем, запланировано ли сообщение на сегодня
            query = select(SchedulerTask).where(
                and_(
                    SchedulerTask.chat_id == message.chat.id,
                    SchedulerTask.task_type == TaskType.DAILY_MESSAGE,
                    SchedulerTask.scheduled_time >= now,
                    SchedulerTask.scheduled_time <= now.replace(hour=23, minute=59, second=59),
                    SchedulerTask.is_completed == False
                )
            )
            
            result = await session.execute(query)
            pending_task = result.scalar_one_or_none()
            
            if pending_task:
                await message.answer(
                    f"Локатор пидоров запланирован на сегодня, ждите ⏰"
                )
            else:
                await message.answer(
                    "На сегодня нет запланированных сообщений. Возможно, оно запланировано на завтра 🤔"
                )

    except Exception as e:
        await message.reply("Произошла ошибка при проверке статуса ежедневного сообщения.")
        logging.error(f"Error in cmd_daily_status: {e}")

class DailyHandler:
    async def _get_user_by_id(self, session, user_id: int, chat_id: int) -> User | None:
        """Получает пользователя по ID и чату."""
        query = select(User).where(
            and_(
                User.user_id == user_id,
                User.chat_id == chat_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _update_user_rating(self, session, user_id: int, rating_delta: int):
        """Обновляет рейтинг пользователя."""
        await session.execute(
            update(UserStats)
            .where(UserStats.id == user_id)
            .values(rating=UserStats.rating + rating_delta)
        )

    async def _get_random_users(self, session, chat_id: int, limit: int = 2) -> list[User]:
        """Выбирает случайных активных пользователей из чата."""
        query = select(User).where(
            and_(
                User.chat_id == chat_id,
                User.is_active == True
            )
        ).order_by(func.random()).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()

    async def _update_stats(self, session, master_id: int, slave_id: int, initiator_id: int):
        """Обновляет статистику после daily."""
        await session.execute(
            update(UserStats)
            .where(
                or_(
                    UserStats.id == master_id,
                    UserStats.id == slave_id,
                    UserStats.id == initiator_id
                )
            )
            .values(
                master_count=case(
                    (UserStats.id == master_id, UserStats.master_count + 1),
                    else_=UserStats.master_count
                ),
                slave_count=case(
                    (UserStats.id == slave_id, UserStats.slave_count + 1),
                    else_=UserStats.slave_count
                ),
                launched_count=case(
                    (UserStats.id == initiator_id, UserStats.launched_count + 1),
                    else_=UserStats.launched_count
                ),
                rating=case(
                    (UserStats.id == master_id, UserStats.rating + 100),
                    (UserStats.id == slave_id, UserStats.rating + 50),
                    else_=UserStats.rating
                )
            )
        )

    def _format_result_message(self, master: User, slave: User, initiator: User) -> str:
        """Форматирует сообщение с результатами."""
        master_username = f"@{master.username}" if master.username else f"ID: {master.user_id}"
        slave_username = f"@{slave.username}" if slave.username else f"ID: {slave.user_id}"
        initiator_username = f"@{initiator.username}" if initiator.username else f"ID: {initiator.user_id}"
        
        return (
            f"🎯 Локатор обнаружил:\n\n"
            f"👑 {hbold('Пидор дня')}: {master_username}!\n"
            f"🔗 {hbold('Пассив дня')}: {slave_username}!\n\n"
            f"🎮 Локатор запустил: {initiator_username}"
        )

@router.callback_query(F.data.startswith("daily_first_"))
async def handle_daily_first(callback: CallbackQuery, session, vk_handler: VKHandler):
    try:
        chat_id = callback.message.chat.id
        initiator_user_id = callback.from_user.id
        task_id = int(callback.data.split('_')[-1])
        
        # Проверяем, что задача была запланирована на сегодня
        query = select(SchedulerTask).where(SchedulerTask.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            await callback.message.reply("Произошла ошибка при поиске задачи.")
            return
            
        # Сравниваем текущий день с днем задачи
        utc_tz = pytz.UTC
        current_date = datetime.now(utc_tz).date()
        task_date = task.scheduled_time.astimezone(utc_tz).date()
        
        if current_date != task_date:
            # Удаляем клавиатуру у сообщения
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.reply(
                "Вы не успели выполнить команду в нужный день! 😢"
            )
            return
        
        handler = DailyHandler()
        # Проверяем пользователя и обновляем рейтинг
        user = await handler._get_user_by_id(session, initiator_user_id, chat_id)
        if not user:
            await callback.message.reply("Вы не учавствуете в поиске пидоров! Используйте /addme чтобы добавиться в поиск.")
            return
        
        # Удаляем сообщение с кнопкой
        await callback.message.delete()
        
        await handler._update_user_rating(session, user.id, 25)
        
        # Выбираем случайных пользователей
        random_users = await handler._get_random_users(session, chat_id)
        if len(random_users) != 2:
            await callback.message.answer("Кажется у вас не достаточно пидоров в чате.")
            return
        
        master, slave = random_users
        
        # Обновляем статистику
        await handler._update_stats(session, master.id, slave.id, user.id)
        await session.commit()
        
        # Получаем случайное фото
        photo_url = await vk_handler.get_random_photo()

        # Формируем результат с информацией об инициаторе
        result_message = handler._format_result_message(master, slave, user)
        
        # Отправляем результат с фото, если оно есть
        if photo_url:
            await callback.bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=result_message,
                parse_mode="HTML"
            )
        else:
            # Если фото не удалось получить, отправляем только текст
            await callback.bot.send_message(
                chat_id=chat_id,
                text=result_message,
                parse_mode="HTML"
            )
        
        logging.info(
            f"Выбраны master ({master.username}) и slave ({slave.username}) "
            f"в чате {chat_id}"
        )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке нажатия кнопки: {e}")
        raise e 