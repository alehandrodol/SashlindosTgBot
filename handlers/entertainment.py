# Стандартные библиотеки
import logging

# Сторонние библиотеки
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

# Локальные импорты
from core.vk_handler import VKHandler

router = Router()

@router.message(Command("picture"))
async def cmd_picture(message: Message, vk_handler: VKHandler, session):
    """Отправляет случайную фотографию из альбома группы."""
    try:
        if await vk_handler.is_picture_limited(session, message.from_user.id, message.chat.id):
            await message.delete()
            return
        photo_url = await vk_handler.get_random_photo()
            
        if photo_url:
            # Отправляем фото
            await message.reply_photo(
                photo=photo_url,
                caption="Вот вам пидорская картинка 📸"
            )
        else:
            await message.reply("Фото не нашлось 😢")
        
    except Exception as e:
        await message.reply("Произошла ошибка при получении фотографии.")
        logging.error(f"Error in cmd_picture: {e}") 