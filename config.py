from dataclasses import dataclass
from environs import Env

@dataclass
class TgBot:
    token: str

@dataclass
class DatabaseConfig:
    host: str
    port: int
    password: str
    user: str
    database: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig

def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN')
        ),
        db=DatabaseConfig(
            host=env('DB_HOST'),
            port=env.int('DB_PORT'),
            password=env('DB_PASS'),
            user=env('DB_USER'),
            database=env('DB_NAME')
        )
    )