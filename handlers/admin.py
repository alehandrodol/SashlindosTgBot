# Стандартные библиотеки
import logging
import pytz

# Сторонние библиотеки
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

# Локальные импорты
from database.models import Chat
from core.scheduler import Scheduler

router = Router()

ALEHANDRO_ID = 454397941
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class AdminMessageStates(StatesGroup):
    waiting_for_message = State()

@router.message(Command("send"))
async def cmd_send(message: Message, state: FSMContext):
    """Обработчик команды отправки сообщения в чаты."""
        
    if message.chat.type != 'private':
        return
    
    # Проверка на админа
    if message.from_user.id != ALEHANDRO_ID:
        await message.reply("У вас нет прав для использования этой команды!")
        return
        
    try:
        # Извлекаем ID чата из аргументов команды
        args = message.text.split()
        if len(args) > 1:
            target_chat_id = args[1]
            await state.update_data(chat_id=target_chat_id)
        else:
            await state.update_data(chat_id='all')
            
        await state.set_state(AdminMessageStates.waiting_for_message)
        await message.reply(
            "Пожалуйста, ответьте на это сообщение текстом, "
            "который нужно отправить в чат(ы)"
        )
        
    except Exception as e:
        await message.reply("Произошла ошибка при обработке команды.")
        logging.error(f"Error in cmd_send: {e}")

@router.message(StateFilter(AdminMessageStates.waiting_for_message), F.reply_to_message)
async def process_message_to_send(message: Message, session, state: FSMContext):
    """Обработчик сообщения для отправки."""
    try:
        # Получаем сохраненный chat_id
        data = await state.get_data()
        target_chat_id = data.get('chat_id')
        
        if target_chat_id == 'all':
            # Получаем все активные чаты
            query = select(Chat).where(Chat.is_active == True)
            result = await session.execute(query)
            chats = result.scalars().all()
            
            success_count = 0
            for chat in chats:
                try:
                    await message.bot.send_message(
                        chat_id=chat.chat_id,
                        text=message.text
                    )
                    success_count += 1
                except Exception as e:
                    logging.error(f"Ошибка при отправке в чат {chat.chat_id}: {e}")
                    
            await message.reply(f"Сообщение отправлено в {success_count} чатов")
        else:
            # Отправляем в конкретный чат
            try:
                await message.bot.send_message(
                    chat_id=target_chat_id,
                    text=message.text
                )
                await message.reply("Сообщение успешно отправлено")
            except Exception as e:
                await message.reply("Ошибка при отправке сообщения в указанный чат")
                logging.error(f"Error sending message to chat {target_chat_id}: {e}")
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        await message.reply("Произошла ошибка при отправке сообщения.")
        logging.error(f"Error in process_message_to_send: {e}")
        await state.clear()

@router.message(Command("tasks"))
async def cmd_tasks(message: Message, scheduler: Scheduler):
    """Показывает все запланированные задачи."""
    
    if message.chat.type != 'private':
        return
    
    # Проверка на админа
    if message.from_user.id != ALEHANDRO_ID:
        await message.reply("У вас нет прав для использования этой команды!")
        return
        
    try:
        jobs = scheduler.get_scheduled_jobs()
        
        if not jobs:
            await message.reply("Нет запланированных задач.")
            return
            
        # Форматируем сообщение
        lines = ["📅 <b>Запланированные задачи:</b>\n"]
        
        for job in jobs:
            job_time = job['next_run_time']
            formatted_time = job_time.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
            
            lines.append(
                f"🔹 ID: {job['id']}\n"
                f"⏰ Следующий запуск: {formatted_time}\n"
                f"📍 Чат ID: {job['args'][0] if job['args'] else 'N/A'}\n"
                f"ℹ️ Тип: {job['trigger']}\n"
            )
            
        await message.reply("\n".join(lines), parse_mode="HTML")
        
    except Exception as e:
        await message.reply("Произошла ошибка при получении списка задач.")
        logging.error(f"Error in cmd_tasks: {e}")

