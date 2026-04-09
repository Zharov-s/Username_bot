from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import Settings
from app.services.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from app.telegram.handlers import router


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    limiter = InMemoryRateLimiter(limit_per_minute=settings.bot_rate_limit_per_minute)
    dp.message.middleware(RateLimitMiddleware(limiter))
    dp.include_router(router)
    return dp


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запуск и краткая справка"),
        BotCommand(command="help", description="Подробная инструкция"),
        BotCommand(command="import", description="Импорт своего CSV-источника"),
        BotCommand(command="lookup_file", description="Проверка списка номеров"),
        BotCommand(command="stats", description="Статистика разрешённого источника"),
        BotCommand(command="cancel", description="Отменить текущий режим"),
    ]
    await bot.set_my_commands(commands)
