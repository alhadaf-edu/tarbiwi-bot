from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import add_or_update_user, is_user_banned, get_setting
from config import MAIN_GROUP_ID

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Track or update user
        await add_or_update_user(user.id, user.full_name, user.username)

        # Check if user is banned
        if await is_user_banned(user.id):
            if isinstance(event, Message):
                await event.answer("⛔️ تم حظر حسابك من استخدام تربوي بوت من قبل الإدارة.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔️ حسابك محظور من الاستخدام.", show_alert=True)
            return

        return await handler(event, data)

async def check_user_membership(bot: Bot, user_id: int) -> bool:
    """
    Checks if user is member of the diploma group if check is enabled in settings.
    """
    enabled = await get_setting("membership_check_enabled", "0")
    if enabled != "1":
        return True

    group_id_val = await get_setting("main_group_id", "")
    group_id = int(group_id_val) if group_id_val.strip().lstrip("-").isdigit() else MAIN_GROUP_ID
    if not group_id:
        return True

    try:
        member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        # In case bot has no rights or network glitch, do not block user
        return True
