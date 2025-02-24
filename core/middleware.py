import logging
from typing import Any, Awaitable, Callable, List
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from vk_api.vk_api import VkApi
from core.scheduler import Scheduler
from core.vk_handler import VKHandler


class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        data["scheduler"] = self._scheduler
        return await handler(event, data) 
    
class VKMiddleware(BaseMiddleware):
    def __init__(self, token: str) -> None:
        vk_session = VkApi(token=token)
        self._vk_handler = VKHandler(vk_session.get_api())
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        data["vk_handler"] = self._vk_handler    
        return await handler(event, data) 