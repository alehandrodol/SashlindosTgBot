import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from core.vk_handler import VKHandler

router = Router()

@router.message(Command("picture"))
async def cmd_picture(message: Message, vk_handler: VKHandler, session):
    """Отправляет случайную фотографию из альбома группы."""
    try:
        photo_url, error = await vk_handler.get_random_photo(
            session,
            message.from_user.id,
            message.chat.id,
            check_limit=True
        )
        
        if error:
            await message.reply(error)
            return
            
        # Отправляем фото
        await message.reply_photo(
            photo=photo_url,
            caption="Вот вам пидорская картинка 📸"
        )
        
    except Exception as e:
        await message.reply("Произошла ошибка при получении фотографии.")
        logging.error(f"Error in cmd_picture: {e}") 