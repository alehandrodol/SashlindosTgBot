import logging
import random
from vk_api.vk_api import VkApiMethod

class VKHandler:
    def __init__(self, vk: VkApiMethod):
        self._vk = vk

    def _get_photo_url(self, photo: dict) -> str:
        """Получает URL фотографии максимального качества."""
        # Сначала ищем тип 'o' (оригинал), если нет - берем максимальный по ширине
        photo_url = max(photo['sizes'], key=lambda x: x['width'])['url']
            
        return photo_url

    def get_random_photo(self, group_id: str, album_id: str) -> tuple[str, str]:
        """
        Получает случайную фотографию из альбома группы.
        
        Returns:
            tuple[str, str]: (photo_url, error_message)
        """
        try:
            # Получаем размер альбома
            size = self._vk.photos.get_albums(owner_id=group_id, album_ids=album_id)['items'][0]['size']

            if size == 0:
                return None, "В альбоме нет фотографий 😢"
            
            # Получаем случайную фотографию
            photo = self._vk.photos.get(
                owner_id=group_id,
                album_id=album_id,
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