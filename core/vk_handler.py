# Стандартные библиотеки
import logging
import random
from datetime import datetime

# Сторонние библиотеки
import pytz
from sqlalchemy import select, and_
from vk_api.vk_api import VkApiMethod

# Локальные импорты
from database.models import User, UserStats

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class VKHandler:
    GROUP_ID = '-209871225'
    ALBUM_ID = '282103569'

    def __init__(self, vk: VkApiMethod):
        self._vk = vk

    def _get_photo_url(self, photo: dict) -> str:
        """Получает URL фотографии максимального качества."""
        # Сначала ищем тип 'o' (оригинал), если нет - берем максимальный по ширине
        photo_url = max(photo['sizes'], key=lambda x: x['width'])['url']
            
        return photo_url

    async def check_user_limit(self, session, user_id: int, chat_id: int) -> tuple[bool, str]:
        """Проверяет, может ли пользователь использовать команду сегодня."""
        query = (
            select(UserStats)
            .join(User)
            .where(
                and_(
                    User.user_id == user_id,
                    User.chat_id == chat_id
                )
            )
        )
        result = await session.execute(query)
        stats = result.scalar_one_or_none()
        
        if not stats:
            return False, "Вы не зарегистрированы в системе!"
        
        today = datetime.now(MOSCOW_TZ).date()
        
        if stats.last_picture_date == today:
            return False, "Вы уже использовали команду сегодня! Попробуйте завтра 😉"
            
        stats.last_picture_date = today
        await session.commit()
        
        return True, ""

    async def get_random_photo(self, session, user_id: int, chat_id: int, check_limit: bool = False) -> tuple[str | None, str]:
        """Получает случайную фотографию из альбома группы."""
        # Проверяем лимит пользователя только если check_limit=True
        if check_limit:
            can_use, error_message = await self.check_user_limit(session, user_id, chat_id)
            if not can_use:
                return None, error_message

        try:
            # Получаем размер альбома
            size = self._vk.photos.get_albums(owner_id=self.GROUP_ID, album_ids=self.ALBUM_ID)['items'][0]['size']

            if size == 0:
                return None, "В альбоме нет фотографий 😢"
            
            # Получаем случайную фотографию
            photo = self._vk.photos.get(
                owner_id=self.GROUP_ID,
                album_id=self.ALBUM_ID,
                count=1,
                offset=random.randint(0, size - 1)
            )['items'][0]
            
            # Получаем URL фотографии
            photo_url = self._get_photo_url(photo)
            logging.info(f"Получен URL фото: {photo_url}")
            
            return photo_url, None
            
        except Exception as e:
            error_msg = f"Ошибка при получении фотографии: {e}"
            logging.error(error_msg)
            return None, error_msg 