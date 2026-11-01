import shutil
import datetime
from pathlib import Path
from config import DB_PATH

async def create_backup() -> Path:
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"tarbiwi_backup_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_file)
    return backup_file
