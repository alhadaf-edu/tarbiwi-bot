from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Builds the 4 main menu buttons requested:
    1. عرض المنهج الدراسي
    2. البحث عن ملف
    3. مشاركة ملف جديد
    4. روابط المجموعات المهمة
    Plus Admin Panel button for admins.
    """
    buttons = [
        [InlineKeyboardButton(text="📚 عرض المنهج الدراسي", callback_data="curriculum_main")],
        [InlineKeyboardButton(text="🔍 البحث عن ملف", callback_data="search_main")],
        [InlineKeyboardButton(text="📤 مشاركة ملف جديد", callback_data="upload_main")],
        [InlineKeyboardButton(text="🔗 روابط المجموعات المهمة", callback_data="group_links_main")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ لوحة تحكم المشرف", callback_data="admin_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_and_home_buttons(back_callback: str) -> list[list[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(text="🔙 رجوع", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")
        ]
    ]

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء العملية والعودة", callback_data="home")]
    ])
