import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from core.vk_handler import VKHandler

router = Router()

GROUP_ID = '-209871225'
ALBUM_ID = '282103569'

@router.message(Command("picture"))
async def cmd_picture(message: Message, vk_handler: VKHandler):
    """Отправляет случайную фотографию из альбома группы."""
    try:
        photo_url, error = vk_handler.get_random_photo(GROUP_ID, ALBUM_ID)
        
        if error:
            await message.reply(error)
            return
            
        # Отправляем фото
        await message.reply_photo(
            photo=photo_url,
            caption="Случайная фотография из альбома 📸"
        )
        
    except Exception as e:
        await message.reply("Произошла ошибка при получении фотографии.")
        logging.error(f"Error in cmd_picture: {e}") 