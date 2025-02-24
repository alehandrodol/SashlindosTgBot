from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
import logging

from database.models import User, UserStats

router = Router()

class StatsHandler:
    @staticmethod
    async def _get_chat_users_stats(
        session,
        chat_id: int,
        order_by_field = UserStats.rating
    ) -> list[tuple[User, UserStats]]:
        """
        Получает всех пользователей чата с их статистикой.
        
        Args:
            session: Сессия базы данных
            chat_id: ID чата
            order_by_field: Поле для сортировки (по умолчанию rating)
        
        Returns:
            list[tuple[User, UserStats]]: Список пар (пользователь, статистика)
        """
        query = (
            select(User, UserStats)
            .join(UserStats, User.id == UserStats.id)
            .where(User.chat_id == chat_id)
            .order_by(
                User.is_active.desc(),  # Сначала активные
                order_by_field.desc()   # Затем по указанному полю
            )
        )
        result = await session.execute(query)
        return result.all()

    @staticmethod
    def _format_stats_line(
        user: User,
        stats: UserStats,
        is_command_user: bool,
        field: str = 'rating'
    ) -> str:
        """
        Форматирует строку статистики пользователя.
        
        Args:
            user: Пользователь
            stats: Статистика пользователя
            is_command_user: Является ли пользователь вызвавшим команду
            field: Поле статистики ('rating', 'master_count', 'slave_count')
        """
        name = user.username or f"User{user.user_id}"
        
        # Получаем значение и суффикс в зависимости от поля
        value = getattr(stats, field)
        suffix = {
            'rating': 'очков',
            'master_count': 'раз(а)',
            'slave_count': 'раз(а)'
        }.get(field, '')
        
        # Формируем базовую строку
        line = f"{name}: {value} {suffix}"
        
        # Добавляем клоуна если это вызвавший команду пользователь
        if is_command_user:
            line = f"{line} 🤡"
        
        # Зачеркиваем неактивных пользователей
        if not user.is_active:
            line = f"{line}"
            
        return line

@router.message(Command("ratings"))
async def cmd_ratings(message: Message, session):
    """Показывает рейтинг всех участников чата."""
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        handler = StatsHandler()
        
        # Получаем всех пользователей с их статистикой
        users_with_stats = await handler._get_chat_users_stats(
            session,
            message.chat.id,
            UserStats.rating
        )
        
        if not users_with_stats:
            await message.reply("В этом чате пока нет зарегистрированных пользователей!")
            return
        
        # Формируем список
        lines = ["📊 <b>Рейтинг пидорасов:</b>\n"]
        
        # Добавляем активных пользователей
        active_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'rating')
            for user, stats in users_with_stats
            if user.is_active
        ]
        lines.extend(active_users)
        
        # Добавляем разделитель если есть неактивные пользователи
        inactive_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'rating')
            for user, stats in users_with_stats
            if not user.is_active
        ]
        if inactive_users:
            lines.append("\n💤 <b>Неактивные пидорасы:</b>")
            lines.extend(inactive_users)
        
        # Отправляем сообщение
        await message.answer(
            "\n".join(lines),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.reply("Произошла ошибка при получении рейтинга.")
        logging.error(f"Error in cmd_ratings: {e}")

@router.message(Command("masters"))
async def cmd_masters(message: Message, session):
    """Показывает статистику мастеров."""
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        handler = StatsHandler()
        
        # Получаем пользователей, сортированных по master_count
        users_with_stats = await handler._get_chat_users_stats(
            session,
            message.chat.id,
            UserStats.master_count
        )
        
        if not users_with_stats:
            await message.reply("В этом чате пока нет зарегистрированных пользователей!")
            return
        
        lines = ["👑 <b>Статистика пидоров дня:</b>\n"]
        
        # Активные пользователи
        active_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'master_count')
            for user, stats in users_with_stats
            if user.is_active
        ]
        lines.extend(active_users)
        
        # Неактивные пользователи
        inactive_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'master_count')
            for user, stats in users_with_stats
            if not user.is_active
        ]
        if inactive_users:
            lines.append("\n💤 <b>Неактивные пидорасы:</b>")
            lines.extend(inactive_users)
        
        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await message.reply("Произошла ошибка при получении статистики мастеров.")
        logging.error(f"Error in cmd_masters: {e}")

@router.message(Command("slaves"))
async def cmd_slaves(message: Message, session):
    """Показывает статистику рабов."""
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        handler = StatsHandler()
        
        # Получаем пользователей, сортированных по slave_count
        users_with_stats = await handler._get_chat_users_stats(
            session,
            message.chat.id,
            UserStats.slave_count
        )
        
        if not users_with_stats:
            await message.reply("В этом чате пока нет зарегистрированных пользователей!")
            return
        
        lines = ["🔗 <b>Статистика пассивов:</b>\n"]
        
        # Активные пользователи
        active_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'slave_count')
            for user, stats in users_with_stats
            if user.is_active
        ]
        lines.extend(active_users)
        
        # Неактивные пользователи
        inactive_users = [
            handler._format_stats_line(user, stats, user.user_id == message.from_user.id, 'slave_count')
            for user, stats in users_with_stats
            if not user.is_active
        ]
        if inactive_users:
            lines.append("\n💤 <b>Неактивные пидорасы:</b>")
            lines.extend(inactive_users)
        
        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await message.reply("Произошла ошибка при получении статистики рабов.")
        logging.error(f"Error in cmd_slaves: {e}") 