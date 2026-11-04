import os
import shutil
import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional, Tuple
import aiohttp
from aiogram import Bot
from aiogram.types import FSInputFile

from config import DB_PATH, ARCHIVE_CHANNEL_ID
from database import get_setting, get_db

logger = logging.getLogger(__name__)

GITHUB_REPO = os.getenv("GITHUB_REPO", "alhadaf-edu/tarbiwi-bot")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
FILE_PATH_IN_REPO = "data/tarbiwi.db"

async def get_github_token() -> str:
    """Retrieve GitHub token from database settings or environment variable."""
    token = await get_setting("github_token", "")
    if token.strip():
        return token.strip()
    return os.getenv("GITHUB_TOKEN", "").strip()

async def sync_db_to_github(commit_message: str = "Auto-sync database from bot") -> Tuple[bool, str]:
    """
    Commits data/tarbiwi.db directly to GitHub repository via GitHub REST API.
    Returns (success, message).
    """
    token = await get_github_token()
    if not token:
        return False, "GITHUB_TOKEN غير مضبوط. يمكنك إدخاله من إعدادات المشرف."

    if not DB_PATH.exists():
        return False, "ملف قاعدة البيانات المحلي غير موجود."

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH_IN_REPO}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TarbiwiBot-Sync"
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Get current file SHA on branch
            sha = None
            async with session.get(f"{url}?ref={GITHUB_BRANCH}", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sha = data.get("sha")
                elif resp.status != 404:
                    err_txt = await resp.text()
                    logger.error(f"GitHub GET error {resp.status}: {err_txt}")
                    return False, f"فشل قراءة الملف من GitHub: كود {resp.status}"

            # 2. Read local db file and encode to base64
            with open(DB_PATH, "rb") as f:
                content_b64 = base64.b64encode(f.read()).decode("utf-8")

            # 3. Commit/PUT to GitHub
            payload = {
                "message": commit_message,
                "content": content_b64,
                "branch": GITHUB_BRANCH
            }
            if sha:
                payload["sha"] = sha

            async with session.put(url, headers=headers, json=payload) as put_resp:
                if put_resp.status in (200, 201):
                    logger.info("Database successfully committed to GitHub!")
                    return True, "تم حفظ ومزامنة قاعدة البيانات إلى GitHub بنجاح! 🎉"
                else:
                    err_txt = await put_resp.text()
                    logger.error(f"GitHub PUT error {put_resp.status}: {err_txt}")
                    return False, f"فشل الحفظ في GitHub: كود {put_resp.status}"
    except Exception as e:
        logger.error(f"Exception during GitHub sync: {e}")
        return False, f"حدث خطأ أثناء الاتصال بـ GitHub: {e}"

async def backup_db_to_telegram(bot: Bot) -> bool:
    """
    Uploads a snapshot of tarbiwi.db to the archive channel and pins it.
    This guarantees persistence across Render restarts even without GitHub token.
    """
    from services.archive import get_effective_archive_channel
    channel = await get_effective_archive_channel()
    if not channel:
        logger.warning("No archive channel configured for db backup.")
        return False

    if not DB_PATH.exists():
        return False

    temp_backup = DB_PATH.parent / f"backup_snapshot_{os.getpid()}.db"
    try:
        shutil.copy2(DB_PATH, temp_backup)
        doc = FSInputFile(str(temp_backup), filename="tarbiwi.db")
        caption = "#DB_BACKUP_AUTO 📦 أحدث نسخة احتياطية لقاعدة البيانات (حفظ تلقائي)"
        msg = await bot.send_document(chat_id=channel, document=doc, caption=caption)
        
        # Pin the message silently so bot can find it on restart
        try:
            await bot.pin_chat_message(chat_id=channel, message_id=msg.message_id, disable_notification=True)
        except Exception as pin_err:
            logger.debug(f"Could not pin backup message: {pin_err}")

        logger.info(f"Database backup snapshot uploaded to archive channel {channel} (msg_id={msg.message_id}).")
        return True
    except Exception as e:
        logger.error(f"Failed to backup db to telegram archive: {e}")
        return False
    finally:
        if temp_backup.exists():
            try:
                temp_backup.unlink()
            except Exception:
                pass

async def count_records_in_db(db_file: Path) -> int:
    """Counts total records across key tables in a sqlite database file."""
    import aiosqlite
    total = 0
    try:
        async with aiosqlite.connect(str(db_file)) as db:
            for tbl in ["files", "videos", "audios", "books", "lectures", "subjects"]:
                try:
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {tbl};")
                    row = await cursor.fetchone()
                    if row:
                        total += row[0]
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Error counting records in {db_file}: {e}")
    return total

async def restore_db_from_telegram_if_needed(bot: Bot) -> bool:
    """
    On startup, inspects pinned message in the archive channel.
    If the pinned backup has more/equal data than local db, restores it.
    """
    from services.archive import get_effective_archive_channel
    channel = await get_effective_archive_channel()
    if not channel:
        return False

    try:
        chat = await bot.get_chat(channel)
        pinned = chat.pinned_message
        if not pinned or not pinned.document:
            return False

        doc = pinned.document
        if not doc.file_name or not doc.file_name.endswith(".db"):
            return False

        logger.info(f"Found pinned database backup in archive channel (file_id={doc.file_id}). Checking if restore needed...")

        temp_download = DB_PATH.parent / "temp_pinned_restore.db"
        await bot.download(doc.file_id, destination=temp_download)

        # Count records in both
        remote_count = await count_records_in_db(temp_download)
        local_count = await count_records_in_db(DB_PATH) if DB_PATH.exists() else 0

        logger.info(f"Database record check: Local={local_count}, Remote={remote_count}")

        if remote_count >= local_count and remote_count > 0:
            shutil.copy2(temp_download, DB_PATH)
            logger.info("🎉 Restored database from pinned archive backup successfully!")
            return True
        else:
            logger.info("Local database is already up-to-date or newer.")
            return False
    except Exception as e:
        logger.warning(f"Could not restore db from telegram: {e}")
        return False
    finally:
        temp_download = DB_PATH.parent / "temp_pinned_restore.db"
        if temp_download.exists():
            try:
                temp_download.unlink()
            except Exception:
                pass

async def trigger_content_sync(bot: Bot, reason: str = "content_upload"):
    """
    Non-blocking background task to sync database to both Telegram Archive and GitHub.
    """
    async def _task():
        try:
            # 1. Always backup to Telegram Archive Channel
            await backup_db_to_telegram(bot)
            # 2. Sync to GitHub if token available
            await sync_db_to_github(commit_message=f"Auto-sync from bot: {reason}")
        except Exception as e:
            logger.warning(f"Background sync task warning: {e}")

    asyncio.create_task(_task())
