import logging

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER

from database.models import Chat, User, UserStats
from sqlalchemy import select
from core.scheduler import Scheduler


router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session, scheduler: Scheduler):
    """Обработчик команды активации бота в чате."""
    if message.chat.type == 'private':
        await message.reply("Привет! Я групповой бот. Добавьте меня в группу для полноценной работы.")
        return

    try:
        handler = RegistrationHandler()
        
        # Проверяем существование чата
        chat = await handler._get_chat(session, message.chat.id)
        
        if chat:
            await message.reply("Бот уже активирован в группе!")
            return
            
        # Создаем новый чат
        chat = await handler._create_chat(session, message.chat.id)
        
        # Настраиваем расписание для нового чата
        await scheduler.setup_chat_job(chat.chat_id)
        await message.reply("Бот успешно активирован в группе!")

    except Exception as e:
        await message.reply("Произошла ошибка при активации бота.")
        logging.error(f"Error in cmd_start: {e}")

class RegistrationHandler:
    @staticmethod
    async def _get_chat(session, chat_id: int) -> Chat | None:
        """Получает существующий чат."""
        query = select(Chat).where(Chat.chat_id == chat_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def _create_chat(session, chat_id: int) -> Chat:
        """Создает новый чат."""
        chat = Chat(chat_id=chat_id)
        session.add(chat)
        await session.commit()
        return chat

    @staticmethod
    async def _get_user(session, user_id: int, chat_id: int) -> User | None:
        """Получает пользователя из базы данных."""
        query = select(User).where(
            User.user_id == user_id,
            User.chat_id == chat_id
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def _create_user(session, user_id: int, chat_id: int, username: str | None, is_active: bool = True) -> User:
        """Создает нового пользователя и его статистику."""
        new_user = User(
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            is_active=is_active
        )
        session.add(new_user)
        await session.flush()

        # Создаем запись в таблице статистики
        new_stats = UserStats(id=new_user.id)
        session.add(new_stats)
        await session.commit()

        return new_user

    @staticmethod
    async def _deactivate_user(session, user: User) -> bool:
        """Деактивирует пользователя в чате.
        
        Returns:
            bool: True если пользователь был активен и деактивирован,
                 False если пользователь уже был неактивен
        """
        if not user.is_active:
            return False
            
        user.is_active = False
        await session.commit()
        return True

    @staticmethod
    async def _setup_new_chat(session, chat: Chat, scheduler: Scheduler) -> bool:
        """Настраивает новый чат и планирует задачи.
        
        Returns:
            bool: True если это новый чат, False если чат уже существовал
        """
        if not chat._sa_instance_state.pending:  # Проверяем, что чат уже существовал
            return False
            
        await session.commit()
        await scheduler.setup_chat_job(chat.chat_id)
        return True

    @staticmethod
    async def _deactivate_chat(session, chat: Chat) -> bool:
        """Деактивирует чат.
        
        Returns:
            bool: True если чат был активен и деактивирован,
                 False если чат уже был неактивен
        """
        if not chat.is_active:
            return False
            
        chat.is_active = False
        await session.commit()
        return True

@router.message(Command("addme"))
async def cmd_addme(message: Message, session):
    """Обработчик команды регистрации пользователя в чате."""
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        handler = RegistrationHandler()
        
        # Проверяем существование чата
        chat = await handler._get_chat(session, message.chat.id)
        if not chat:
            await message.reply("Этот чат не зарегистрирован! Сначала выполните команду /start")
            return

        # Проверяем существование пользователя
        user = await handler._get_user(session, message.from_user.id, message.chat.id)

        if user:
            if not user.is_active:
                user.is_active = True
                await session.commit()
                await message.reply("Вы снова активны в этом чате!")
                return
            await message.reply("Вы уже зарегистрированы в этом чате!")
            return

        # Создаем нового пользователя
        await handler._create_user(
            session,
            message.from_user.id,
            message.chat.id,
            message.from_user.username,
            is_active=True
        )

        await message.reply("Ты успешно зарегистрирован!")

    except Exception as e:
        await message.reply("Произошла ошибка при регистрации.")
        logging.error(f"Error in cmd_addme: {e}")

@router.message(Command("disableme"))
async def cmd_disableme(message: Message, session):
    """Обработчик команды деактивации пользователя в чате."""
    if message.chat.type == 'private':
        await message.reply("Эта команда работает только в групповых чатах!")
        return

    try:
        handler = RegistrationHandler()
        
        # Получаем пользователя
        user = await handler._get_user(session, message.from_user.id, message.chat.id)

        if not user:
            await message.reply("Вы не зарегистрированы в этом чате!")
            return
        
        # Деактивируем пользователя
        if await handler._deactivate_user(session, user):
            await message.reply("Вы успешно деактивированы в этом чате! Используйте /addme чтобы снова стать активным.")
        else:
            await message.reply("Вы уже неактивны в этом чате!")

    except Exception as e:
        await message.reply("Произошла ошибка при деактивации.")
        logging.error(f"Error in cmd_disableme: {e}")

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER))
async def member_leave_chat(event: ChatMemberUpdated, session):
    """Обработчик события когда участника удаляют или он выходит из чата."""
    try:
        handler = RegistrationHandler()
        
        # Получаем пользователя
        user = await handler._get_user(session, event.old_chat_member.user.id, event.chat.id)
        
        if user:
            # Деактивируем пользователя
            await handler._deactivate_user(session, user)
            logging.info(f"Пользователь {user.username or user.user_id} деактивирован в чате {event.chat.id}")
            
    except Exception as e:
        logging.error(f"Ошибка при обработке удаления участника: {e}")

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER))
async def member_join_chat(event: ChatMemberUpdated):
    """Обработчик события когда участник присоединяется к чату."""
    try:

        username = event.new_chat_member.user.username or event.new_chat_member.user.first_name
        await event.bot.send_message(
            chat_id=event.chat.id,
            text=f"Привет, {username}! 👋\n\n"
                    f"Если хочешь участвовать в поиске пидорасов, используй команду /addme"
        )
            
    except Exception as e:
        logging.error(f"Ошибка при обработке присоединения участника: {e}")

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER))
async def bot_removed_from_chat(event: ChatMemberUpdated, session):
    """Обработчик события когда бота удаляют из чата."""
    try:
        handler = RegistrationHandler()
        
        # Получаем чат
        chat = await handler._get_chat(session, event.chat.id)
        
        if chat:
            # Деактивируем чат
            await handler._deactivate_chat(session, chat)
            logging.info(f"Бот был удален из чата {event.chat.id}, чат деактивирован")
            
    except Exception as e:
        logging.error(f"Ошибка при обработке удаления бота из чата: {e}")

@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER))
async def bot_added_to_chat(event: ChatMemberUpdated, session):
    """Обработчик события когда бота добавляют в чат."""
    try:
        handler = RegistrationHandler()
        
        # Проверяем существование чата
        chat = await handler._get_chat(session, event.chat.id)
        
        if chat:
            # Если чат уже существует, активируем его
            chat.is_active = True
            await session.commit()
            await event.bot.send_message(
                chat_id=event.chat.id,
                text="Я вернулся из небытия, да-да - я! 😈"
            )
            logging.info(f"Бот реактивирован в существующем чате {event.chat.id}")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке добавления бота в чат: {e}")