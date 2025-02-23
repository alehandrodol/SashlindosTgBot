from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from core.scheduler import Scheduler

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