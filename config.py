import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin IDs (comma-separated list of integer IDs)
raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = set()
for item in raw_admin_ids.split(","):
    item = item.strip()
    if item.isdigit():
        ADMIN_IDS.add(int(item))

# Main diploma group for membership verification and announcements
MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID", "").strip()
try:
    MAIN_GROUP_ID = int(MAIN_GROUP_ID) if MAIN_GROUP_ID else None
except ValueError:
    pass

# Archive channel / group for permanent telegram file storage
ARCHIVE_CHANNEL_ID = os.getenv("ARCHIVE_CHANNEL_ID", "").strip()
try:
    ARCHIVE_CHANNEL_ID = int(ARCHIVE_CHANNEL_ID) if ARCHIVE_CHANNEL_ID else None
except ValueError:
    pass

DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/tarbiwi.db")

# Security and limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
UPLOAD_RATE_LIMIT_SECONDS = int(os.getenv("UPLOAD_RATE_LIMIT_SECONDS", "10"))

# Forbidden dangerous file extensions
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".vbs", ".js", ".msi", ".jar", 
    ".scr", ".pif", ".com", ".hta", ".cpl", ".ps1", ".reg"
}
