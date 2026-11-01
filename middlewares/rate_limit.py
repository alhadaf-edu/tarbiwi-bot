import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import UPLOAD_RATE_LIMIT_SECONDS

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = UPLOAD_RATE_LIMIT_SECONDS):
        self.limit = limit
        self.user_last_action: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Apply rate limiting specifically on message media uploads to avoid spamming the bot
        if isinstance(event, Message) and (event.document or event.video or event.photo):
            now = time.time()
            last_time = self.user_last_action.get(user.id, 0)
            if now - last_time < self.limit:
                remaining = int(self.limit - (now - last_time))
                await event.answer(f"⏳ يرجى الانتظار {remaining} ثانية قبل رفع ملف آخر منعاً للضغط على الخادم.")
                return
            self.user_last_action[user.id] = now

        return await handler(event, data)
