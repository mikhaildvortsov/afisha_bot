from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import ADMIN_IDS, SUPER_ADMIN_IDS
from database import get_admin_ids


async def is_super_admin(telegram_id: int) -> bool:
    return telegram_id in SUPER_ADMIN_IDS


async def is_admin(telegram_id: int) -> bool:
    """Суперадмины и админы из окружения — всегда админы, остальные проверяются по БД."""
    if telegram_id in SUPER_ADMIN_IDS or telegram_id in ADMIN_IDS:
        return True
    return telegram_id in await get_admin_ids()


async def get_all_admin_ids() -> list[int]:
    """Все получатели админских уведомлений, без повторов."""
    ids = list(SUPER_ADMIN_IDS) + list(ADMIN_IDS) + await get_admin_ids()
    return list(dict.fromkeys(ids))


class IsAdmin(Filter):
    """Права проверяются на каждом апдейте, поэтому новые админы работают без перезапуска."""

    async def __call__(self, event: TelegramObject) -> bool:
        if not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return False
        return await is_admin(event.from_user.id)


class IsSuperAdmin(Filter):
    async def __call__(self, event: TelegramObject) -> bool:
        if not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return False
        return await is_super_admin(event.from_user.id)
