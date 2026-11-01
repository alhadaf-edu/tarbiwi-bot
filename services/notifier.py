import logging
from typing import Optional
from aiogram import Bot
from config import MAIN_GROUP_ID
from database import get_setting

logger = logging.getLogger(__name__)

async def get_effective_main_group() -> Optional[int | str]:
    db_val = await get_setting("main_group_id", "")
    if db_val.strip():
        val = db_val.strip()
        if val.startswith("-100") or (val.lstrip("-").isdigit()):
            return int(val)
        return val
    return MAIN_GROUP_ID

async def notify_new_content(
    bot: Bot,
    content_type: str,
    title: str,
    uploader_name: str,
    day_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    lecture_name: Optional[str] = None,
    spec_name: Optional[str] = None,
    category_name: Optional[str] = None
) -> None:
    """
    Sends an announcement to the main diploma group if notifications are enabled.
    """
    notif_setting = await get_setting("notifications_enabled", "1")
    if notif_setting != "1":
        return

    main_group = await get_effective_main_group()
    if not main_group:
        return

    lines = [
        "📢 <b>تمت إضافة محتوى تعليمي جديد!</b> 📚",
        f"🏷 <b>النوع:</b> {content_type}",
        f"📌 <b>العنوان:</b> {title}"
    ]

    if day_name:
        lines.append(f"📅 <b>اليوم:</b> {day_name}")
    if subject_name:
        lines.append(f"📖 <b>المادة:</b> {subject_name}")
    if spec_name:
        lines.append(f"🎯 <b>التخصص:</b> {spec_name}")
    if lecture_name:
        lines.append(f"🎓 <b>المحاضرة:</b> {lecture_name}")
    if category_name:
        lines.append(f"📂 <b>التصنيف:</b> {category_name}")

    lines.append(f"👤 <b>بواسطة:</b> {uploader_name}")
    lines.append("\n🤖 تصفح المحتوى الآن عبر <b>تربوي بوت</b>!")

    text = "\n".join(lines)
    try:
        await bot.send_message(chat_id=main_group, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to send notification to main group {main_group}: {e}")
