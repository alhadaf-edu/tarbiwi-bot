from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_upload_menu_keyboard() -> InlineKeyboardMarkup:
    """The upload options"""
    buttons = [
        [InlineKeyboardButton(text="1️⃣ 📖 إضافة كتاب دراسي", callback_data="upload_opt_book")],
        [InlineKeyboardButton(text="2️⃣ 🗓 إضافة جدول دراسي", callback_data="upload_opt_schedule")],
        [InlineKeyboardButton(text="3️⃣ 💡 اقتراح مادة جديدة", callback_data="upload_opt_suggest_subject")],
        [InlineKeyboardButton(text="4️⃣ 🎓 إضافة محاضرة جديدة", callback_data="upload_opt_lecture")],
        [InlineKeyboardButton(text="5️⃣ 🎥 رفع فيديو لمحاضرة", callback_data="upload_opt_video")],
        [InlineKeyboardButton(text="6️⃣ 🎙 رفع تسجيل صوتي لمحاضرة", callback_data="upload_opt_audio")],
        [InlineKeyboardButton(text="7️⃣ 📁 رفع ملف لمحاضرة موجودة", callback_data="upload_opt_file")],
        [InlineKeyboardButton(text="🏠 العودة للقائمة الرئيسية", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_consecutive_upload_keyboard(lecture_id: int, category: str) -> InlineKeyboardMarkup:
    """Requirement 7.7: Consecutive uploads keyboard"""
    buttons = [
        [InlineKeyboardButton(text="📤 رفع ملف آخر لنفس المحاضرة والتصنيف", callback_data=f"consec_upload:{lecture_id}:{category}")],
        [InlineKeyboardButton(text="🏠 العودة للقائمة الرئيسية", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard(confirm_callback: str = "confirm_publish") -> InlineKeyboardMarkup:
    """Confirmation keyboard before publishing"""
    buttons = [
        [InlineKeyboardButton(text="✅ تأكيد ونشر الآن", callback_data=confirm_callback)],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skip_or_cancel_keyboard() -> InlineKeyboardMarkup:
    """For optional steps like description"""
    buttons = [
        [InlineKeyboardButton(text="⏭ تخطي هذه الخطوة", callback_data="skip_step")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_category_selection_keyboard() -> InlineKeyboardMarkup:
    """Category picker during file upload"""
    buttons = [
        [InlineKeyboardButton(text="🤖 ملخص AI", callback_data="pick_cat:ai")],
        [InlineKeyboardButton(text="✍️ شرح بخط اليد", callback_data="pick_cat:handwritten")],
        [InlineKeyboardButton(text="📊 PowerPoint الدكتور", callback_data="pick_cat:powerpoint")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
