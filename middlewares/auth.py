import asyncio
from typing import Callable, Dict, Any, Awaitable, Optional
import logging
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from database import add_or_update_user, is_user_banned, is_admin, get_setting
from config import MAIN_GROUP_ID

logger = logging.getLogger(__name__)

async def auto_delete_messages(messages: list, delay: int = 15):
    """Silently delete messages after delay so the group stays completely clean."""
    try:
        await asyncio.sleep(delay)
        for msg in messages:
            if msg:
                try:
                    await msg.delete()
                except Exception:
                    pass
    except Exception:
        pass
    group_id_val = await get_setting("main_group_id", "")
    if not group_id_val.strip() and MAIN_GROUP_ID:
        group_id_val = str(MAIN_GROUP_ID)

    clean_val = group_id_val.strip()
    if clean_val.startswith("-100") or clean_val.lstrip("-").isdigit():
        try:
            return int(clean_val)
        except ValueError:
            pass
    # Default fallback group ID specified by user
    return -1004407684546

async def get_main_group_invite_link(bot: Bot) -> str:
    # 1. Setting from database
    link = await get_setting("main_group_invite_link", "")
    if link.strip():
        return link.strip()

    # 2. Check group_links table for Telegram link
    try:
        from database import get_group_links
        links = await get_group_links(include_hidden=True)
        for l in links:
            url = l.get("url", "")
            if "t.me/+ru9uMBNoXZ0xM2E8" in url or "t.me/+" in url or "t.me/joinchat" in url:
                return url
    except Exception:
        pass

    # 3. Dynamic chat link
    group_id = await get_effective_group_id()
    if group_id:
        try:
            chat = await bot.get_chat(chat_id=group_id)
            if chat.invite_link:
                return chat.invite_link
        except Exception:
            pass

    # 4. Fallback known link specified by user
    return "https://t.me/+ru9uMBNoXZ0xM2E8"

async def check_user_membership(bot: Bot, user_id: int) -> bool:
    """
    Checks if user is member of the diploma group.
    """
    group_id = await get_effective_group_id()
    if not group_id:
        return True

    try:
        member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        return member.status in ("creator", "administrator", "member", "restricted")
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "user not found" in err_msg or "participant" in err_msg or "user_not_participant" in err_msg:
            return False
        if "chat not found" in err_msg or "bot is not a member" in err_msg:
            logger.error(f"Bot cannot check membership in group {group_id}: {e}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Error checking membership for user {user_id} in {group_id}: {e}")
        return True

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

        # 1. Chat Type Check: Ensure all interactions happen exclusively in private chat
        chat = data.get("event_chat")
        if not chat:
            if hasattr(event, "message") and event.message:
                chat = event.message.chat
            elif hasattr(event, "callback_query") and event.callback_query and event.callback_query.message:
                chat = event.callback_query.message.chat
            elif isinstance(event, Message):
                chat = event.chat
            elif isinstance(event, CallbackQuery) and event.message:
                chat = event.message.chat

        if chat and chat.type != "private":
            target_msg = None
            if hasattr(event, "message") and event.message:
                target_msg = event.message
            elif isinstance(event, Message):
                target_msg = event

            if target_msg and target_msg.text and target_msg.text.startswith("/"):
                bot: Optional[Bot] = data.get("bot")
                bot_user = await bot.get_me() if bot else None
                bot_uname = bot_user.username if bot_user else "Tarbawe_3Bot"
                user_mention = user.mention_html() if hasattr(user, "mention_html") else user.full_name
                
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="💬 اضغط هنا لبدء المحادثة في الخاص", url=f"https://t.me/{bot_uname}?start=from_group")
                ]])
                reply_text = (
                    f"👋 أهلاً بك {user_mention}!\n\n"
                    "محادثات وخدمات «تربوي بوت» مخصصة في <b>المحادثات الخاصة</b> فقط للحفاظ على ترتيب ونظام المجموعة 🎓\n\n"
                    "اضغط على الزر أدناه لبدء المحادثة في الخاص 👇"
                )
                try:
                    sent_msg = await target_msg.reply(reply_text, reply_markup=kb, parse_mode="HTML")
                    # Silently delete both user command and bot reply after 15 seconds to keep group 100% clean
                    asyncio.create_task(auto_delete_messages([target_msg, sent_msg], delay=15))
                except Exception:
                    try:
                        await target_msg.delete()
                    except Exception:
                        pass

            # Drop other non-command group events
            return

        # 2. Check if user is banned
        if await is_user_banned(user.id):
            if hasattr(event, "message") and event.message:
                await event.message.answer("⛔️ تم حظر حسابك من استخدام تربوي بوت من قبل الإدارة.")
            elif isinstance(event, Message):
                await event.answer("⛔️ تم حظر حسابك من استخدام تربوي بوت من قبل الإدارة.")
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.answer("⛔️ حسابك محظور من الاستخدام.", show_alert=True)
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔️ حسابك محظور من الاستخدام.", show_alert=True)
            return

        # 3. Membership Check: Bot is only available to Telegram group members
        # Admins always bypass membership check
        user_is_admin = await is_admin(user.id)
        if not user_is_admin:
            bot: Optional[Bot] = data.get("bot")
            if bot:
                is_member = await check_user_membership(bot, user.id)
                if not is_member:
                    # Handle verification button click when still not joined
                    cb = None
                    if hasattr(event, "callback_query") and event.callback_query:
                        cb = event.callback_query
                    elif isinstance(event, CallbackQuery):
                        cb = event

                    if cb and cb.data == "check_join_membership":
                        await cb.answer(
                            "❌ لم يتم التحقق من انضمامك بعد!\nيرجى الضغط على زر «الانضمام لمجموعة الدبلومة» أولاً ثم الضغط هنا مجدداً.",
                            show_alert=True
                        )
                        return
                    elif cb:
                        await cb.answer("⚠️ محتوى البوت مخصص لأعضاء مجموعة الدبلومة فقط. يرجى الانضمام أولاً.", show_alert=True)
                        return

                    msg = None
                    if hasattr(event, "message") and event.message:
                        msg = event.message
                    elif isinstance(event, Message):
                        msg = event

                    if msg:
                        invite_link = await get_main_group_invite_link(bot)
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="👥 الانضمام لمجموعة الدبلومة", url=invite_link)],
                            [InlineKeyboardButton(text="🔄 تحقق من الانضمام", callback_data="check_join_membership")]
                        ])
                        lock_text = (
                            "🔒 <b>عذراً! محتوى البوت مخصص لأعضاء المجموعة فقط 🎓</b>\n\n"
                            "أهلاً بك زميلنا العزيز! للاستفادة من محتويات «تربوي بوت» (المحاضرات، الملخصات، الكتب، الفيديوهات)، "
                            "يجب أن تكون عضواً في مجموعة الدبلومة الرسمية:\n"
                            "👥 <b>دبلومة التأهيل التربوي أون لاين – مجموعة 3</b>\n\n"
                            "👇 <b>خطوات التفعيل:</b>\n"
                            "1️⃣ اضغط على زر <b>«الانضمام لمجموعة الدبلومة 👥»</b> أدناه.\n"
                            "2️⃣ بعد الانضمام للمجموعة، اضغط على زر <b>«🔄 تحقق من الانضمام»</b> ليفتح لك البوت فوراً!"
                        )
                        await msg.answer(lock_text, reply_markup=kb, parse_mode="HTML")
                        return

                    return

        return await handler(event, data)
