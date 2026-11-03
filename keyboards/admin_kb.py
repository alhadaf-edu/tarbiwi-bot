from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🗓 إدارة الأيام الدراسية", callback_data="admin_days"),
            InlineKeyboardButton(text="📅 إدارة المواد والدكاترة", callback_data="admin_subjects")
        ],
        [
            InlineKeyboardButton(text="🎯 إدارة التخصصات", callback_data="admin_specs"),
            InlineKeyboardButton(text="🎓 إدارة المحاضرات", callback_data="admin_lectures")
        ],
        [
            InlineKeyboardButton(text="📚 إدارة الكتب والجداول", callback_data="admin_books_schedules"),
            InlineKeyboardButton(text="📁 إدارة الملفات والتصنيفات", callback_data="admin_files_hub")
        ],
        [
            InlineKeyboardButton(text="🎥 إدارة الفيديوهات", callback_data="admin_videos_hub"),
            InlineKeyboardButton(text="🔗 إدارة روابط المجموعات", callback_data="admin_group_links")
        ],
        [
            InlineKeyboardButton(text="💡 اقتراحات المواد الجديدة", callback_data="admin_suggestions"),
            InlineKeyboardButton(text="👥 إدارة المستخدمين والحظر", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📢 إعدادات الإشعارات والأرشيف", callback_data="admin_settings"),
            InlineKeyboardButton(text="📊 إحصائيات النظام الشاملة", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📋 سجل النشاط الأخير", callback_data="admin_logs"),
            InlineKeyboardButton(text="💾 تنزيل نسخة احتياطية (Backup)", callback_data="admin_download_backup")
        ],
        [
            InlineKeyboardButton(text="🏠 العودة للقائمة الرئيسية", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_links_keyboard(links: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for lnk in links:
        vis = "👁 ظاهر" if lnk["is_visible"] else "🙈 مخفي"
        keyboard.append([
            InlineKeyboardButton(text=f"{lnk['title']} ({vis})", callback_data=f"adm_link_detail:{lnk['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ إضافة رابط جديد", callback_data="adm_add_link")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_link_actions_keyboard(link_id: int, is_visible: bool) -> InlineKeyboardMarkup:
    toggle_text = "🙈 إخفاء الرابط" if is_visible else "👁 إظهار الرابط"
    buttons = [
        [InlineKeyboardButton(text=toggle_text, callback_data=f"adm_toggle_link:{link_id}")],
        [InlineKeyboardButton(text="✏️ تعديل الاسم والرابط", callback_data=f"adm_edit_link:{link_id}")],
        [InlineKeyboardButton(text="🗑 حذف الرابط", callback_data=f"adm_delete_link:{link_id}")],
        [InlineKeyboardButton(text="🔙 رجوع للروابط", callback_data="admin_group_links")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_file_actions_keyboard(file_id: int, is_hidden: bool) -> InlineKeyboardMarkup:
    hide_text = "👁 إظهار الملف" if is_hidden else "🙈 إخفاء الملف"
    buttons = [
        [InlineKeyboardButton(text="📥 إرسال وتحميل الملف", callback_data=f"file_get:{file_id}")],
        [InlineKeyboardButton(text=hide_text, callback_data=f"adm_file_toggle_hide:{file_id}")],
        [InlineKeyboardButton(text="✏️ تعديل اسم الملف", callback_data=f"adm_file_edit_name:{file_id}")],
        [InlineKeyboardButton(text="🗑 حذف الملف نهائياً", callback_data=f"adm_file_delete:{file_id}")],
        [InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_settings_keyboard(notif_enabled: bool, check_membership: bool) -> InlineKeyboardMarkup:
    notif_text = "🔔 الإشعارات: مفعلة (إيقاف)" if notif_enabled else "🔕 الإشعارات: معطلة (تفعيل)"
    check_text = "🛡 فحص عضوية المجموعة: مفعل" if check_membership else "🔓 فحص عضوية المجموعة: معطل"
    buttons = [
        [InlineKeyboardButton(text=notif_text, callback_data="adm_toggle_setting:notifications_enabled")],
        [InlineKeyboardButton(text=check_text, callback_data="adm_toggle_setting:membership_check_enabled")],
        [InlineKeyboardButton(text="📁 ضبط معرّف قناة الأرشيف", callback_data="adm_set_archive_channel")],
        [InlineKeyboardButton(text="👥 ضبط معرّف المجموعة الرئيسية", callback_data="adm_set_main_group")],
        [InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
