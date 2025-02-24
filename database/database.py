# Стандартные библиотеки
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict

# Сторонние библиотеки
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Локальные импорты
from config import Config


# Создаем класс с настройками для базы данных
class DatabaseConfig:
    database_url: str
    def __init__(self, config: Config):
        self.database_url = f"postgresql+asyncpg://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.database}"

# Создаем engine и сессию
class Database:
    _session_maker: sessionmaker[AsyncSession]

    def __init__(self, config: DatabaseConfig):
        engine = create_async_engine(
            config.database_url,
            echo=False,
        )
        self._session_maker = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_maker() as session:
            yield session 

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.database = db
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async for session in self.database.get_session():
            if session is None:
                raise RuntimeError("Session is None")
            data['session'] = session
            return await handler(event, data)