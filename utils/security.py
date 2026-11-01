import re
from pathlib import Path
from typing import Tuple
from config import DANGEROUS_EXTENSIONS, MAX_FILE_SIZE_MB

def is_safe_file_name(file_name: str) -> Tuple[bool, str]:
    if not file_name:
        return True, ""
    
    ext = Path(file_name).suffix.lower()
    if ext in DANGEROUS_EXTENSIONS:
        return False, f"عذراً، الامتداد {ext} غير مسموح به لأسباب أمنية."
    
    return True, ""

def is_file_size_acceptable(file_size_bytes: int) -> Tuple[bool, str]:
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"حجم الملف ({file_size_bytes / (1024*1024):.1f}MB) يتجاوز الحد المسموح به للبوت ({MAX_FILE_SIZE_MB}MB)."
    return True, ""

def is_valid_url(url: str) -> bool:
    if not url:
        return False
    url_pattern = re.compile(
        r'^(https?:\/\/)?' # http:// or https://
        r'(([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,6})|(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))' # domain or ip
        r'(:\d+)?(\/.*)?$', re.IGNORECASE
    )
    return bool(url_pattern.match(url.strip()))
