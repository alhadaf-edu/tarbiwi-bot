from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.pagination import build_pagination_keyboard
from database import CATEGORY_NAMES, CATEGORY_ICONS

def get_curriculum_menu() -> InlineKeyboardMarkup:
    """Submenu of 'عرض المنهج الدراسي'"""
    buttons = [
        [InlineKeyboardButton(text="📖 تحميل الكتب الدراسية", callback_data="books_list:0")],
        [InlineKeyboardButton(text="📅 مواد الأيام الدراسية", callback_data="study_days_list")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_days_keyboard(days: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Ordered 4 days buttons: الأربعاء، الخميس، الجمعة، السبت"""
    keyboard = []
    day_icons = {"الأربعاء": "1️⃣", "الخميس": "2️⃣", "الجمعة": "3️⃣", "السبت": "4️⃣"}
    for day in days:
        icon = day_icons.get(day["name"], "📅")
        keyboard.append([InlineKeyboardButton(text=f"{icon} {day['name']}", callback_data=f"day_view:{day['id']}")])
    keyboard.append([
        InlineKeyboardButton(text="🔙 رجوع", callback_data="curriculum_main"),
        InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subjects_keyboard(day_id: int, day_name: str, subjects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Displays subjects for the day with doctor name below/with the subject"""
    keyboard = []
    for s in subjects:
        doc = f" - {s['doctor_name']}" if s.get("doctor_name") else ""
        text = f"📖 {s['name']}{doc}"
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"subj_view:{s['id']}")])

    keyboard.append([
        InlineKeyboardButton(text="🔙 رجوع للأيام", callback_data="study_days_list"),
        InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_specializations_keyboard(subject_id: int, specs: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Displays specializations for طرق تدريس (2)"""
    keyboard = []
    spec_icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    for idx, spec in enumerate(specs):
        icon = spec_icons[idx % len(spec_icons)]
        keyboard.append([InlineKeyboardButton(text=f"{icon} {spec['name']}", callback_data=f"spec_view:{spec['id']}")])

    keyboard.append([
        InlineKeyboardButton(text="🔙 رجوع للمواد", callback_data="study_days_list"),
        InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_lectures_keyboard(
    subject_id: int,
    lectures: List[Dict[str, Any]],
    spec_id: Optional[int] = None,
    back_callback: str = "study_days_list"
) -> InlineKeyboardMarkup:
    """Displays lectures list dynamically"""
    keyboard = []
    for lec in lectures:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {lec['name']}", callback_data=f"lec_view:{lec['id']}")])

    # Button to quickly add lecture from here
    add_cb = f"quick_add_lec:{subject_id}:{spec_id if spec_id else 0}"
    keyboard.append([InlineKeyboardButton(text="➕ إضافة محاضرة جديدة", callback_data=add_cb)])

    keyboard.append([
        InlineKeyboardButton(text="🔙 رجوع", callback_data=back_callback),
        InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_lecture_detail_keyboard(lecture_id: int, back_callback: str) -> InlineKeyboardMarkup:
    """Shows video and files menu for a specific lecture"""
    buttons = [
        [InlineKeyboardButton(text="🎥 فيديو المحاضرة", callback_data=f"lec_videos:{lecture_id}:0")],
        [InlineKeyboardButton(text="📂 ملفات المحاضرة", callback_data=f"lec_files_cats:{lecture_id}")],
        [
            InlineKeyboardButton(text="🔙 رجوع للمحاضرات", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_categories_keyboard(lecture_id: int, counts: Dict[str, int]) -> InlineKeyboardMarkup:
    """Displays the 3 mandatory categories with file counts"""
    buttons = [
        [InlineKeyboardButton(
            text=f"🤖 ملخص AI ({counts.get('ai', 0)})",
            callback_data=f"lec_cat_files:{lecture_id}:ai:0"
        )],
        [InlineKeyboardButton(
            text=f"✍️ شرح بخط اليد ({counts.get('handwritten', 0)})",
            callback_data=f"lec_cat_files:{lecture_id}:handwritten:0"
        )],
        [InlineKeyboardButton(
            text=f"📊 PowerPoint الدكتور ({counts.get('powerpoint', 0)})",
            callback_data=f"lec_cat_files:{lecture_id}:powerpoint:0"
        )],
        [
            InlineKeyboardButton(text="🔙 رجوع للمحاضرة", callback_data=f"lec_view:{lecture_id}"),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_category_files_keyboard(
    files: List[Dict[str, Any]],
    lecture_id: int,
    category: str,
    page: int = 0,
    page_size: int = 6
) -> InlineKeyboardMarkup:
    """Builds paginated keyboard of files within a specific category"""
    def builder(f):
        name = f['file_name']
        if len(name) > 35:
            name = name[:32] + "..."
        return InlineKeyboardButton(text=f"📄 {name}", callback_data=f"file_get:{f['id']}")

    prefix = f"lec_cat_files:{lecture_id}:{category}"
    extra = [
        [InlineKeyboardButton(text="➕ رفع ملف جديد لهذا التصنيف", callback_data=f"quick_upload_file:{lecture_id}:{category}")],
        [
            InlineKeyboardButton(text="🔙 رجوع للتصنيفات", callback_data=f"lec_files_cats:{lecture_id}"),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]
    return build_pagination_keyboard(files, page, page_size, builder, prefix, extra)

def get_videos_keyboard(
    videos: List[Dict[str, Any]],
    lecture_id: int,
    page: int = 0,
    page_size: int = 6
) -> InlineKeyboardMarkup:
    """Builds paginated keyboard of videos for a lecture"""
    def builder(v):
        title = v['title']
        if len(title) > 35:
            title = title[:32] + "..."
        icon = "🎬" if v["video_type"] == "telegram_video" else "🔗"
        return InlineKeyboardButton(text=f"{icon} {title}", callback_data=f"video_get:{v['id']}")

    prefix = f"lec_videos:{lecture_id}"
    extra = [
        [InlineKeyboardButton(text="➕ إضافة فيديو لهذه المحاضرة", callback_data=f"quick_upload_video:{lecture_id}")],
        [
            InlineKeyboardButton(text="🔙 رجوع للمحاضرة", callback_data=f"lec_view:{lecture_id}"),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]
    return build_pagination_keyboard(videos, page, page_size, builder, prefix, extra)

def get_books_keyboard(
    books: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = 6
) -> InlineKeyboardMarkup:
    """Builds paginated keyboard for Books"""
    def builder(b):
        title = b['title']
        if len(title) > 35:
            title = title[:32] + "..."
        return InlineKeyboardButton(text=f"📚 {title}", callback_data=f"book_get:{b['id']}")

    prefix = "books_list"
    extra = [
        [InlineKeyboardButton(text="➕ إضافة كتاب دراسي جديد", callback_data="start_upload_book")],
        [
            InlineKeyboardButton(text="🔙 رجوع للمنهج", callback_data="curriculum_main"),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]
    return build_pagination_keyboard(books, page, page_size, builder, prefix, extra)
