import logging
from typing import Optional, Tuple
from aiogram import Bot
from config import ARCHIVE_CHANNEL_ID
from database import get_setting

logger = logging.getLogger(__name__)

async def get_effective_archive_channel() -> Optional[int | str]:
    """Retrieves archive channel from database settings or falls back to config."""
    db_val = await get_setting("archive_channel_id", "")
    if db_val.strip():
        val = db_val.strip()
        if val.startswith("-100") or (val.lstrip("-").isdigit()):
            return int(val)
        return val
    return ARCHIVE_CHANNEL_ID

async def archive_document(
    bot: Bot,
    file_id: str,
    caption: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Sends/archives the uploaded document into the archive channel/group.
    Returns (archive_message_id, file_id).
    If archive channel is not configured, logs gracefully and returns (None, file_id).
    """
    channel = await get_effective_archive_channel()
    if not channel:
        logger.warning("Archive channel is not configured. Saving local file_id without telegram channel archiving.")
        return None, file_id

    try:
        msg = await bot.send_document(
            chat_id=channel,
            document=file_id,
            caption=caption
        )
        return msg.message_id, msg.document.file_id
    except Exception as e:
        logger.error(f"Failed to archive document to {channel}: {e}")
        # Return the original file_id so user's workflow does not crash
        return None, file_id

async def archive_video(
    bot: Bot,
    file_id: str,
    caption: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Archives a video file into the archive channel.
    """
    channel = await get_effective_archive_channel()
    if not channel:
        return None, file_id

    try:
        msg = await bot.send_video(
            chat_id=channel,
            video=file_id,
            caption=caption
        )
        return msg.message_id, msg.video.file_id
    except Exception as e:
        logger.error(f"Failed to archive video to {channel}: {e}")
        return None, file_id

async def archive_audio(
    bot: Bot,
    file_id: str,
    caption: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Archives an audio file into the archive channel.
    """
    channel = await get_effective_archive_channel()
    if not channel:
        return None, file_id

    try:
        msg = await bot.send_audio(
            chat_id=channel,
            audio=file_id,
            caption=caption
        )
        # msg.audio may be None if Telegram converts it to a document
        if msg.audio:
            return msg.message_id, msg.audio.file_id
        elif msg.document:
            return msg.message_id, msg.document.file_id
        return msg.message_id, file_id
    except Exception as e:
        logger.error(f"Failed to archive audio to {channel}: {e}")
        return None, file_id
