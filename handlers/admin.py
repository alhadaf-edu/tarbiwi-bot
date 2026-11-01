from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from database import (
    is_admin, get_statistics, get_activity_logs, get_all_users, set_user_ban,
    get_group_links, add_group_link, update_group_link, delete_group_link,
    toggle_group_link_visibility, get_pending_suggestions, review_suggestion,
    get_setting, set_setting, get_study_days, get_day_by_id, get_subjects_by_day, get_subject_by_id,
    update_subject, delete_subject, get_specializations, get_specialization_by_id,
    update_specialization, delete_specialization, add_specialization,
    get_lectures, get_lecture_by_id, update_lecture, delete_lecture,
    get_files, get_file_by_id, update_file, delete_file, toggle_file_hidden,
    get_videos, delete_video, toggle_video_hidden,
    get_books, delete_book, get_schedules, delete_schedule
)
from keyboards.admin_kb import (
    get_admin_dashboard_keyboard, get_admin_links_keyboard, get_admin_link_actions_keyboard,
    get_admin_file_actions_keyboard, get_admin_settings_keyboard
)
from keyboards.main_kb import get_cancel_keyboard
from utils.states import AdminStates
from services.backup import create_backup

router = Router(name="admin")

async def ensure_admin(callback_or_msg) -> bool:
    user_id = callback_or_msg.from_user.id
    if not await is_admin(user_id):
        if isinstance(callback_or_msg, CallbackQuery):
            await callback_or_msg.answer("⛔️ هذه اللوحة مخصصة لمشرفي البوت فقط.", show_alert=True)
        else:
            await callback_or_msg.answer("⛔️ هذه الأوامر مخصصة لمشرفي البوت فقط.")
        return False
    return True

# --- Main Admin Dashboard ---
@router.callback_query(F.data == "admin_main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.clear()
    stats = await get_statistics()
    text = (
        "⚙️ <b>لوحة تحكم المشرف - تربوي بوت:</b>\n\n"
        f"👥 المستخدمون: <b>{stats.get('users', 0)}</b> | 🚫 المحظورون: <b>{stats.get('banned_users', 0)}</b>\n"
        f"📖 المواد: <b>{stats.get('subjects', 0)}</b> | 🎓 المحاضرات: <b>{stats.get('lectures', 0)}</b>\n"
        f"📁 الملفات: <b>{stats.get('files', 0)}</b> (🤖 AI: {stats.get('ai_files', 0)} | ✍️ يدوي: {stats.get('handwritten_files', 0)} | 📊 PPT: {stats.get('ppt_files', 0)})\n"
        f"🎥 الفيديوهات: <b>{stats.get('videos', 0)}</b> | 📚 الكتب: <b>{stats.get('books', 0)}</b>\n\n"
        "اختر القسم الذي تريد إدارته:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_dashboard_keyboard(), parse_mode="HTML")
    await callback.answer()

# --- System Statistics & Active Users ---
@router.callback_query(F.data.startswith("admin_stats"))
async def cb_admin_stats(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    parts = callback.data.split(":")
    page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    stats = await get_statistics()
    users = await get_all_users()

    # Pagination for users list
    page_size = 8
    total_users = len(users)
    total_pages = max(1, (total_users + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * page_size
    page_users = users[start_idx:start_idx + page_size]

    text = (
        "📊 <b>إحصائيات النظام الشاملة:</b>\n\n"
        f"👥 <b>إجمالي المستخدمين:</b> {stats.get('users', 0)} | 🚫 <b>المحظورون:</b> {stats.get('banned_users', 0)}\n"
        f"📖 <b>المواد:</b> {stats.get('subjects', 0)} | 🎓 <b>المحاضرات:</b> {stats.get('lectures', 0)}\n"
        f"📁 <b>الملفات:</b> {stats.get('files', 0)} (🤖 {stats.get('ai_files', 0)} | ✍️ {stats.get('handwritten_files', 0)} | 📊 {stats.get('ppt_files', 0)})\n"
        f"🎥 <b>الفيديوهات:</b> {stats.get('videos', 0)} | 📚 <b>الكتب:</b> {stats.get('books', 0)} | 🗓 <b>الجداول:</b> {stats.get('schedules', 0)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>المستخدمون المسجلون بالبوت ({total_users}):</b>\n"
    )

    if not users:
        text += "<i>لا يوجد مستخدمون مسجلون بعد.</i>\n"
    else:
        text += f"<i>(صفحة {page + 1} من {total_pages})</i>\n\n"
        for idx, u in enumerate(page_users, start=start_idx + 1):
            role_badge = "👑 مشرف" if u.get("is_admin") else ("🚫 محظور" if u.get("is_banned") else "👤 عضو")
            uname = f"@{u['username']}" if u.get("username") else "بدون يوزر"
            fname = u.get("full_name") or "مستخدم"
            join_dt = str(u.get("joined_at", ""))[:16]
            text += (
                f"{idx}. {role_badge} <b>{fname}</b> ({uname})\n"
                f"   ├ 🆔: <code>{u['user_id']}</code>\n"
                f"   └ 📅 انضم: {join_dt}\n\n"
            )

    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"admin_stats:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"admin_stats:{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(text="🔄 تحديث الإحصائيات", callback_data=f"admin_stats:{page}"),
        InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")
    ])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# --- Activity Logs ---
@router.callback_query(F.data == "admin_logs")
async def cb_admin_logs(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    logs = await get_activity_logs(limit=20)
    text = "📋 <b>سجل النشاط الأخير في البوت:</b>\n\n"
    if not logs:
        text += "<i>لا توجد أنشطة مسجلة حتى الآن.</i>"
    else:
        for l in logs:
            uname = l.get('username') or l.get('full_name') or l.get('user_id')
            time_str = str(l.get('created_at'))[:16]
            text += f"• [{time_str}] <b>{uname}</b>: {l['action']} - {l.get('details','')}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# --- Backup Download ---
@router.callback_query(F.data == "admin_download_backup")
async def cb_admin_download_backup(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    await callback.answer("⏳ جاري إنشاء النسخة الاحتياطية...")
    try:
        backup_file = await create_backup()
        doc = FSInputFile(str(backup_file), filename=backup_file.name)
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=doc,
            caption="💾 <b>نسخة احتياطية كاملة لقاعدة بيانات تربوي بوت (SQLite)</b>\nتحتفظ بكافة المواد، المحاضرات، الملفات والروابط.",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"❌ حدث خطأ أثناء إنشاء النسخة الاحتياطية: {e}")

# --- Group Links Management ---
@router.callback_query(F.data == "admin_group_links")
async def cb_admin_group_links(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    links = await get_group_links(include_hidden=True)
    text = (
        "🔗 <b>إدارة روابط المجموعات والقنوات:</b>\n\n"
        "اضغط على أي رابط لتعديله أو إخفائه أو حذفه، أو أضف رابطاً جديداً:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_links_keyboard(links), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_add_link")
async def cb_adm_add_link(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.set_state(AdminStates.waiting_for_new_link_title)
    await callback.message.edit_text("أرسل <b>اسم الرابط أو القناة</b> (مثال: قناة المناقشات الرسمية):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_link_title)
async def adm_link_title_received(message: Message, state: FSMContext):
    await state.update_data(link_title=message.text.strip())
    await state.set_state(AdminStates.waiting_for_new_link_url)
    await message.answer("أرسل <b>رابط القناة أو المجموعة</b> (مثال: https://t.me/...):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(AdminStates.waiting_for_new_link_url)
async def adm_link_url_received(message: Message, state: FSMContext):
    data = await state.get_data()
    url = message.text.strip()
    await add_group_link(title=data["link_title"], url=url)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة للروابط", callback_data="admin_group_links")]])
    await message.answer("✅ <b>تمت إضافة الرابط بنجاح!</b> ويظهر الآن فوراً في البوت.", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_link_detail:"))
async def cb_adm_link_detail(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    link_id = int(callback.data.split(":")[1])
    links = await get_group_links(include_hidden=True)
    lnk = next((l for l in links if l["id"] == link_id), None)
    if not lnk:
        await callback.answer("الرابط غير موجود.", show_alert=True)
        return
    status = "ظاهر للأعضاء" if lnk["is_visible"] else "مخفي عن الأعضاء"
    text = (
        f"🔗 <b>تفاصيل الرابط:</b>\n\n"
        f"🏷 <b>الاسم:</b> {lnk['title']}\n"
        f"🌐 <b>الرابط:</b> {lnk['url']}\n"
        f"👁 <b>الحالة:</b> {status}\n"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_link_actions_keyboard(link_id, lnk["is_visible"]), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_toggle_link:"))
async def cb_adm_toggle_link(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    link_id = int(callback.data.split(":")[1])
    await toggle_group_link_visibility(link_id)
    await callback.answer("✅ تم تغيير حالة ظهور الرابط.")
    # Refresh detail
    links = await get_group_links(include_hidden=True)
    lnk = next((l for l in links if l["id"] == link_id), None)
    if lnk:
        status = "ظاهر للأعضاء" if lnk["is_visible"] else "مخفي عن الأعضاء"
        text = f"🔗 <b>تفاصيل الرابط:</b>\n\n🏷 <b>الاسم:</b> {lnk['title']}\n🌐 <b>الرابط:</b> {lnk['url']}\n👁 <b>الحالة:</b> {status}\n"
        await callback.message.edit_text(text, reply_markup=get_admin_link_actions_keyboard(link_id, lnk["is_visible"]), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_delete_link:"))
async def cb_adm_delete_link(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    link_id = int(callback.data.split(":")[1])
    await delete_group_link(link_id)
    await callback.answer("🗑 تم حذف الرابط بنجاح.", show_alert=True)
    links = await get_group_links(include_hidden=True)
    await callback.message.edit_text("🔗 <b>إدارة روابط المجموعات والقنوات:</b>", reply_markup=get_admin_links_keyboard(links), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_edit_link:"))
async def cb_adm_edit_link(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    link_id = int(callback.data.split(":")[1])
    links = await get_group_links(include_hidden=True)
    lnk = next((l for l in links if l["id"] == link_id), None)
    if not lnk:
        await callback.answer("الرابط غير موجود.", show_alert=True)
        return
    await state.update_data(edit_link_id=link_id)
    await state.set_state(AdminStates.waiting_for_edit_link_title)
    text = (
        f"✏️ <b>تعديل الرابط:</b>\n\n"
        f"🏷 <b>الاسم الحالي:</b> {lnk['title']}\n"
        f"🌐 <b>الرابط الحالي:</b> <code>{lnk['url']}</code>\n\n"
        "أرسل <b>الاسم الجديد</b> للرابط أو المجموعة:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_link_title)
async def adm_edit_link_title_received(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(new_link_title=title)
    await state.set_state(AdminStates.waiting_for_edit_link_url)
    await message.answer(
        f"🏷 الاسم المختار: <b>{title}</b>\n\nأرسل الآن <b>الرابط الجديد</b> (رابط ويب يبدأ بـ https:// أو معرّف يبدأ بـ @):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_for_edit_link_url)
async def adm_edit_link_url_received(message: Message, state: FSMContext):
    url = message.text.strip()
    data = await state.get_data()
    link_id = data.get("edit_link_id")
    title = data.get("new_link_title")
    if not link_id or not title:
        await state.clear()
        await message.answer("⚠️ حدث خطأ أو انتهت صلاحية الجلسة، يرجى المحاولة مجدداً.")
        return
    await update_group_link(link_id, title=title, url=url)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة لإدارة الروابط", callback_data="admin_group_links")]])
    await message.answer(
        f"✅ <b>تم تحديث بيانات الرابط بنجاح!</b>\n\n"
        f"🏷 <b>الاسم:</b> {title}\n"
        f"🌐 <b>الرابط:</b> {url}",
        reply_markup=kb,
        parse_mode="HTML"
    )

# --- Subjects & Doctors Management ---
@router.callback_query(F.data == "admin_subjects")
async def cb_admin_subjects(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 مواد يوم {d['name']}", callback_data=f"adm_day_subj:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])
    await callback.message.edit_text("📅 <b>إدارة المواد وأعضاء هيئة التدريس:</b>\nاختر اليوم الدراسي:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_day_subj:"))
async def cb_adm_day_subj(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    day_id = int(callback.data.split(":")[1])
    subjects = await get_subjects_by_day(day_id)
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(text=f"✏️ {s['name']} ({s.get('doctor_name','')})", callback_data=f"adm_edit_subj_menu:{s['id']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للأيام", callback_data="admin_subjects")])
    await callback.message.edit_text("اختر المادة لتعديل اسمها أو اسم الدكتور المسند إليها:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_edit_subj_menu:"))
async def cb_adm_edit_subj_menu(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    subject_id = int(callback.data.split(":")[1])
    s = await get_subject_by_id(subject_id)
    await state.update_data(subject_id=subject_id)
    await state.set_state(AdminStates.waiting_for_edit_subject_name)
    text = (
        f"📖 <b>المادة الحالية:</b> {s['name']}\n"
        f"👨‍🏫 <b>الدكتور الحالي:</b> {s.get('doctor_name') or 'غير محدد'}\n\n"
        "أرسل <b>الاسم الجديد للمادة</b>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_subject_name)
async def adm_subj_new_name(message: Message, state: FSMContext):
    await state.update_data(new_subj_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_edit_subject_doctor)
    await message.answer("أرسل <b>اسم عضو هيئة التدريس الجديد</b>:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(AdminStates.waiting_for_edit_subject_doctor)
async def adm_subj_new_doc(message: Message, state: FSMContext):
    data = await state.get_data()
    doc_name = message.text.strip()
    await update_subject(data["subject_id"], data["new_subj_name"], doc_name)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع لإدارة المواد", callback_data="admin_subjects")]])
    await message.answer("✅ <b>تم تحديث بيانات المادة والدكتور بنجاح!</b> وتظهر فوراً للأعضاء.", reply_markup=kb, parse_mode="HTML")

# --- Specializations Management (طرق تدريس 2) ---
@router.callback_query(F.data == "admin_specs")
async def cb_admin_specs(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    # Find subject طرق تدريس 2
    from database import get_db
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM subjects WHERE has_specializations = 1 LIMIT 1;")
        row = await cursor.fetchone()
        if not row:
            await callback.answer("لم يتم العثور على مادة طرق تدريس (2)", show_alert=True)
            return
        toroq_id = row["id"]

    specs = await get_specializations(toroq_id)
    keyboard = []
    for sp in specs:
        keyboard.append([InlineKeyboardButton(text=f"🎯 {sp['name']}", callback_data=f"adm_spec_action:{sp['id']}")])
    keyboard.append([InlineKeyboardButton(text="➕ إضافة تخصص جديد", callback_data=f"adm_add_spec:{toroq_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])

    text = "🎯 <b>إدارة التخصصات الفرعية لمادة طرق تدريس (2):</b>\nاختر التخصص لتعديله أو حذفه:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_spec_action:"))
async def cb_adm_spec_action(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    spec_id = int(callback.data.split(":")[1])
    spec = await get_specialization_by_id(spec_id)
    await state.update_data(spec_id=spec_id)
    await state.set_state(AdminStates.waiting_for_edit_spec_name)
    await callback.message.edit_text(f"🎯 التخصص الحالي: <b>{spec['name']}</b>\n\nأرسل <b>الاسم الجديد للتخصص</b>:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_spec_name)
async def adm_spec_name_edited(message: Message, state: FSMContext):
    data = await state.get_data()
    new_name = message.text.strip()
    await update_specialization(data["spec_id"], new_name)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع للتخصصات", callback_data="admin_specs")]])
    await message.answer(f"✅ تم تعديل اسم التخصص إلى <b>{new_name}</b> بنجاح!", reply_markup=kb, parse_mode="HTML")

# --- Subject Suggestions Review ---
@router.callback_query(F.data == "admin_suggestions")
async def cb_admin_suggestions(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    suggestions = await get_pending_suggestions()
    text = "💡 <b>اقتراحات المواد الجديدة المقدمة من الأعضاء:</b>\n\n"
    keyboard = []
    if not suggestions:
        text += "<i>لا توجد اقتراحات معلقة حالياً.</i>"
    else:
        for s in suggestions:
            text += f"• <b>{s['name']}</b> (يوم {s['day_name']}) - د/ {s.get('doctor_name','غير محدد')} | بواسطة: {s['user_name']}\n"
            keyboard.append([
                InlineKeyboardButton(text=f"✅ اعتماد {s['name']}", callback_data=f"sugg_accept:{s['id']}:{s['day_id']}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"sugg_reject:{s['id']}")
            ])

    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("sugg_accept:"))
async def cb_sugg_accept(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    parts = callback.data.split(":")
    sugg_id = int(parts[1])
    day_id = int(parts[2])
    suggestions = await get_pending_suggestions()
    s = next((x for x in suggestions if x["id"] == sugg_id), None)
    if s:
        from database import add_subject
        await add_subject(day_id, s["name"], s.get("doctor_name", ""))
        await review_suggestion(sugg_id, "approved")
        await callback.answer("✅ تم اعتماد المادة وإضافتها للجدول بنجاح!", show_alert=True)
    await cb_admin_suggestions(callback)

@router.callback_query(F.data.startswith("sugg_reject:"))
async def cb_sugg_reject(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    sugg_id = int(callback.data.split(":")[1])
    await review_suggestion(sugg_id, "rejected")
    await callback.answer("❌ تم رفض الاقتراح.")
    await cb_admin_suggestions(callback)

# --- Users & Ban Management ---
@router.callback_query(F.data.startswith("admin_users"))
async def cb_admin_users(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    parts = callback.data.split(":")
    page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    users = await get_all_users()
    banned = [u for u in users if u["is_banned"]]

    page_size = 8
    total_users = len(users)
    total_pages = max(1, (total_users + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * page_size
    page_users = users[start_idx:start_idx + page_size]

    text = (
        "👥 <b>إدارة المستخدمين والحظر:</b>\n\n"
        f"📊 إجمالي المستخدمين: <b>{total_users}</b> | 🚫 المحظورون: <b>{len(banned)}</b>\n\n"
        f"📋 <b>قائمة الحسابات المسجلة:</b> <i>(صفحة {page + 1} من {total_pages})</i>\n\n"
    )

    if not users:
        text += "<i>لا يوجد مستخدمون مسجلون بعد.</i>\n\n"
    else:
        for idx, u in enumerate(page_users, start=start_idx + 1):
            role_badge = "👑 مشرف" if u.get("is_admin") else ("🚫 محظور" if u.get("is_banned") else "👤 عضو")
            uname = f"@{u['username']}" if u.get("username") else "بدون يوزر"
            fname = u.get("full_name") or "مستخدم"
            text += f"{idx}. {role_badge} <b>{fname}</b> ({uname}) 🆔 <code>{u['user_id']}</code>\n"
        text += "\n"

    text += "لإلغاء حظر أو حظر مستخدم، اضغط على أحد الأزرار أدناه:"

    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"admin_users:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"admin_users:{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(text="🚫 حظر مستخدم بالمعرف (ID)", callback_data="adm_ban_user"),
        InlineKeyboardButton(text="✅ فك حظر مستخدم بالمعرف (ID)", callback_data="adm_unban_user")
    ])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_ban_user")
async def cb_adm_ban_user(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.set_state(AdminStates.waiting_for_ban_user_id)
    await callback.message.edit_text("أرسل <b>معرّف المستخدم (Telegram User ID)</b> المراد حظره:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_user_id)
async def adm_ban_user_id_received(message: Message, state: FSMContext):
    uid_str = message.text.strip()
    if not uid_str.isdigit():
        await message.answer("⚠️ يرجى إدخال رقم المعرّف (ID) بصيغة صحيحة.", reply_markup=get_cancel_keyboard())
        return
    uid = int(uid_str)
    await set_user_ban(uid, True)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 إدارة المستخدمين", callback_data="admin_users")]])
    await message.answer(f"🚫 تم حظر المستخدم ذو المعرف ({uid}) بنجاح ومنعه من استخدام البوت.", reply_markup=kb)

@router.callback_query(F.data == "adm_unban_user")
async def cb_adm_unban_user(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.set_state(AdminStates.waiting_for_unban_user_id)
    await callback.message.edit_text("أرسل <b>معرّف المستخدم (Telegram User ID)</b> لإلغاء حظره:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_unban_user_id)
async def adm_unban_user_id_received(message: Message, state: FSMContext):
    uid_str = message.text.strip()
    if not uid_str.isdigit():
        await message.answer("⚠️ يرجى إدخال رقم المعرّف بصيغة صحيحة.", reply_markup=get_cancel_keyboard())
        return
    uid = int(uid_str)
    await set_user_ban(uid, False)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 إدارة المستخدمين", callback_data="admin_users")]])
    await message.answer(f"✅ تم فك الحظر عن المستخدم ({uid}) بنجاح.", reply_markup=kb)

# --- Settings & Archive / Main Group Setup ---
@router.callback_query(F.data == "admin_settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    notif = (await get_setting("notifications_enabled", "1")) == "1"
    check_m = (await get_setting("membership_check_enabled", "0")) == "1"
    arch = await get_setting("archive_channel_id", "غير محدد")
    main_g = await get_setting("main_group_id", "غير محدد")

    text = (
        "📢 <b>إعدادات الإشعارات والأرشيف والمجموعات:</b>\n\n"
        f"📁 قناة الأرشيف: <code>{arch}</code>\n"
        f"👥 مجموعة الدبلومة الرئيسية: <code>{main_g}</code>\n"
        f"🔔 إشعارات النشر التلقائي: {'مفعلة ✅' if notif else 'معطلة ❌'}\n"
        f"🛡 التحقق من عضوية المجموعة قبل الرفع: {'مفعل ✅' if check_m else 'معطل (مفتوح للجميع) 🔓'}\n\n"
        "يمكنك التبديل والتعديل بالضغط على الأزرار:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_settings_keyboard(notif, check_m), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_toggle_setting:"))
async def cb_adm_toggle_setting(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    key = callback.data.split(":")[1]
    curr = await get_setting(key, "0")
    new_val = "0" if curr == "1" else "1"
    await set_setting(key, new_val)
    await callback.answer("✅ تم تحديث الإعداد فوراً.")
    await cb_admin_settings(callback)

@router.callback_query(F.data == "adm_set_archive_channel")
async def cb_adm_set_archive_channel(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.set_state(AdminStates.waiting_for_archive_channel)
    text = (
        "📁 <b>ضبط معرّف قناة/مجموعة الأرشيف:</b>\n\n"
        "أرسل معرّف القناة (ID يبدأ عادة بـ <code>-100...</code>) أو اسم المستخدم (مثال: @my_archive_channel):\n"
        "<i>ملاحظة: تأكد من إضافة البوت كمشرف في القناة ولديه صلاحية نشر الرسائل والملفات.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_archive_channel)
async def adm_archive_channel_received(message: Message, state: FSMContext):
    val = message.text.strip()
    await set_setting("archive_channel_id", val)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة للإعدادات", callback_data="admin_settings")]])
    await message.answer(f"✅ تم حفظ معرّف قناة الأرشيف: <code>{val}</code>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "adm_set_main_group")
async def cb_adm_set_main_group(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await state.set_state(AdminStates.waiting_for_main_group)
    text = (
        "👥 <b>ضبط معرّف مجموعة الدبلومة الرئيسية:</b>\n\n"
        "أرسل معرّف المجموعة (مثال: <code>-1001234567890</code>) لإرسال إشعارات النشر وفحص عضوية الأعضاء:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_main_group)
async def adm_main_group_received(message: Message, state: FSMContext):
    val = message.text.strip()
    await set_setting("main_group_id", val)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة للإعدادات", callback_data="admin_settings")]])
    await message.answer(f"✅ تم حفظ معرّف مجموعة الدبلومة الرئيسية: <code>{val}</code>", reply_markup=kb, parse_mode="HTML")

# --- Files Management Hub ---
@router.callback_query(F.data == "admin_files_hub")
async def cb_admin_files_hub(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    text = (
        "📁 <b>إدارة ملفات المحاضرات:</b>\n\n"
        "يمكنك البحث عن أي ملف من خلال زر «🔍 البحث عن ملف» في القائمة الرئيسية واستخدام زر التعديل أو الحذف، "
        "أو استعراض الملفات مباشرة عبر المنهج الدراسي حيث يمكنك إدارة كل ملف على حدة."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 تصفح المنهج وإدارة الملفات", callback_data="curriculum_main")],
        [InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# --- Admin File Actions (Edit, Hide, Delete singly) ---
@router.callback_query(F.data.startswith("adm_file_toggle_hide:"))
async def cb_adm_file_toggle_hide(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    file_id = int(callback.data.split(":")[1])
    await toggle_file_hidden(file_id)
    await callback.answer("✅ تم تغيير حالة إخفاء/إظهار الملف فوراً.")

@router.callback_query(F.data.startswith("adm_file_delete:"))
async def cb_adm_file_delete(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    file_id = int(callback.data.split(":")[1])
    await delete_file(file_id)
    await callback.answer("🗑 تم حذف الملف نهائياً دون التأثير على بقية الملفات.", show_alert=True)
    await callback.message.delete()

# --- Admin File Edit Name ---
@router.callback_query(F.data.startswith("adm_file_edit_name:"))
async def cb_adm_file_edit_name(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    file_id = int(callback.data.split(":")[1])
    file_data = await get_file_by_id(file_id)
    if not file_data:
        await callback.answer("الملف غير موجود.", show_alert=True)
        return
    await state.update_data(edit_file_id=file_id)
    await state.set_state(AdminStates.waiting_for_edit_file_name)
    text = (
        f"✏️ <b>تعديل اسم الملف:</b>\n\n"
        f"📄 <b>الاسم الحالي:</b> {file_data['file_name']}\n\n"
        "أرسل <b>الاسم الجديد</b> للملف:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_file_name)
async def adm_file_new_name_received(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    file_id = data.get("edit_file_id")
    if not file_id:
        await state.clear()
        await message.answer("⚠️ حدث خطأ أو انتهت صلاحية الجلسة.")
        return
    await update_file(file_id, file_name=new_name)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]])
    await message.answer(f"✅ تم تعديل اسم الملف إلى: <b>{new_name}</b> بنجاح!", reply_markup=kb, parse_mode="HTML")

# ==========================================
# إدارة المحاضرات (Lectures Management)
# ==========================================
@router.callback_query(F.data == "admin_lectures")
async def cb_admin_lectures(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 محاضرات يوم {d['name']}", callback_data=f"adm_lec_day:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="➕ إضافة محاضرة جديدة مباشرة", callback_data="upload_opt_lecture")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])
    text = "🎓 <b>إدارة المحاضرات:</b>\n\nاختر اليوم الدراسي لاستعراض وتعديل محاضرات مواده، أو أضف محاضرة جديدة:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_lec_day:"))
async def cb_adm_lec_day(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    day_id = int(callback.data.split(":")[1])
    day = await get_day_by_id(day_id)
    subjects = await get_subjects_by_day(day_id)
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(text=f"📖 {s['name']}", callback_data=f"adm_lec_subj:{s['id']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للأيام", callback_data="admin_lectures")])
    text = f"📅 <b>محاضرات يوم {day['name'] if day else ''}:</b>\n\nاختر المادة:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_lec_subj:"))
async def cb_adm_lec_subj(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    subj_id = int(callback.data.split(":")[1])
    subject = await get_subject_by_id(subj_id)
    if not subject:
        await callback.answer("المادة غير موجودة.", show_alert=True)
        return

    if subject.get("has_specializations"):
        specs = await get_specializations(subj_id)
        keyboard = []
        for sp in specs:
            keyboard.append([InlineKeyboardButton(text=f"🎯 {sp['name']}", callback_data=f"adm_lec_spec:{sp['id']}")])
        keyboard.append([InlineKeyboardButton(text="🔙 رجوع للمواد", callback_data=f"adm_lec_day:{subject['day_id']}")])
        text = f"📖 <b>{subject['name']}</b>\nهذه المادة مقسمة لتخصصات، اختر التخصص لإدارة محاضراته:"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    lectures = await get_lectures(subj_id)
    keyboard = []
    for lec in lectures:
        keyboard.append([
            InlineKeyboardButton(text=f"🎓 {lec['name']}", callback_data=f"lec_view:{lec['id']}"),
            InlineKeyboardButton(text="✏️", callback_data=f"adm_lec_edit:{lec['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"adm_lec_del:{lec['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ إضافة محاضرة لهذه المادة", callback_data="upload_opt_lecture")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للمواد", callback_data=f"adm_lec_day:{subject['day_id']}")])

    text = (
        f"📖 <b>محاضرات مادة {subject['name']}:</b>\n\n"
        f"إجمالي المحاضرات: {len(lectures)}\n"
        "يمكنك الضغط على اسم المحاضرة لعرضها، أو (✏️) للتعديل، أو (🗑) للحذف:"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_lec_spec:"))
async def cb_adm_lec_spec(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    spec_id = int(callback.data.split(":")[1])
    spec = await get_specialization_by_id(spec_id)
    if not spec:
        await callback.answer("التخصص غير موجود.", show_alert=True)
        return

    lectures = await get_lectures(spec["subject_id"], specialization_id=spec_id)
    keyboard = []
    for lec in lectures:
        keyboard.append([
            InlineKeyboardButton(text=f"🎓 {lec['name']}", callback_data=f"lec_view:{lec['id']}"),
            InlineKeyboardButton(text="✏️", callback_data=f"adm_lec_edit:{lec['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"adm_lec_del:{lec['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ إضافة محاضرة لهذا التخصص", callback_data="upload_opt_lecture")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للتخصصات", callback_data=f"adm_lec_subj:{spec['subject_id']}")])

    text = (
        f"🎯 <b>محاضرات {spec['name']}:</b>\n\n"
        f"إجمالي المحاضرات: {len(lectures)}\n"
        "يمكنك الضغط على اسم المحاضرة لعرضها، أو (✏️) للتعديل، أو (🗑) للحذف:"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_lec_edit:"))
async def cb_adm_lec_edit(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    lec_id = int(callback.data.split(":")[1])
    lec = await get_lecture_by_id(lec_id)
    if not lec:
        await callback.answer("المحاضرة غير موجودة.", show_alert=True)
        return
    await state.update_data(edit_lec_id=lec_id)
    await state.set_state(AdminStates.waiting_for_edit_lecture_name)
    text = (
        f"✏️ <b>تعديل اسم المحاضرة:</b>\n\n"
        f"الاسم الحالي: <b>{lec['name']}</b>\n\n"
        "أرسل الاسم الجديد للمحاضرة:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_lecture_name)
async def adm_lec_edit_name_received(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    lec_id = data.get("edit_lec_id")
    if not lec_id:
        await state.clear()
        await message.answer("⚠️ حدث خطأ أو انتهت صلاحية الجلسة.")
        return
    await update_lecture(lec_id, new_name)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع لإدارة المحاضرات", callback_data="admin_lectures")]])
    await message.answer(f"✅ تم تحديث اسم المحاضرة إلى: <b>{new_name}</b> بنجاح!", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_lec_del:"))
async def cb_adm_lec_del(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    lec_id = int(callback.data.split(":")[1])
    await delete_lecture(lec_id)
    await callback.answer("🗑 تم حذف المحاضرة وجميع الملفات المرتبطة بها بنجاح.", show_alert=True)
    await cb_admin_lectures(callback)

# ==========================================
# إدارة الكتب والجداول (Books & Schedules)
# ==========================================
@router.callback_query(F.data == "admin_books_schedules")
async def cb_admin_books_schedules(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    books = await get_books()
    schedules = await get_schedules()
    text = (
        "📚 <b>إدارة الكتب والمراجع والجداول الدراسية:</b>\n\n"
        f"📖 إجمالي الكتب المرفوعة: <b>{len(books)}</b>\n"
        f"🗓 إجمالي الجداول المرفوعة: <b>{len(schedules)}</b>\n\n"
        "اختر القسم لإدارته أو حذف أي محتوى قديم منه:"
    )
    keyboard = [
        [InlineKeyboardButton(text=f"📚 استعراض وحذف الكتب ({len(books)})", callback_data="adm_books_list")],
        [InlineKeyboardButton(text=f"🗓 استعراض وحذف الجداول ({len(schedules)})", callback_data="adm_schedules_list")],
        [
            InlineKeyboardButton(text="➕ رفع كتاب جديد", callback_data="upload_opt_book"),
            InlineKeyboardButton(text="➕ رفع جدول جديد", callback_data="upload_opt_schedule")
        ],
        [InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "adm_books_list")
async def cb_adm_books_list(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    books = await get_books()
    text = "📚 <b>قائمة الكتب والمراجع الدراسية المرفوعة:</b>\n\n"
    keyboard = []
    if not books:
        text += "<i>لا توجد كتب مرفوعة حالياً.</i>"
    else:
        for b in books:
            keyboard.append([
                InlineKeyboardButton(text=f"📖 {b['title'][:26]}", callback_data=f"book_get:{b['id']}"),
                InlineKeyboardButton(text="🗑 حذف", callback_data=f"adm_book_del:{b['id']}")
            ])
    keyboard.append([InlineKeyboardButton(text="➕ رفع كتاب دراسي جديد", callback_data="upload_opt_book")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_books_schedules")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_book_del:"))
async def cb_adm_book_del(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    book_id = int(callback.data.split(":")[1])
    await delete_book(book_id)
    await callback.answer("🗑 تم حذف الكتاب بنجاح.", show_alert=True)
    await cb_adm_books_list(callback)

@router.callback_query(F.data == "adm_schedules_list")
async def cb_adm_schedules_list(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    schedules = await get_schedules()
    text = "🗓 <b>قائمة الجداول الدراسية المرفوعة:</b>\n\n"
    keyboard = []
    if not schedules:
        text += "<i>لا توجد جداول مرفوعة حالياً.</i>"
    else:
        for sc in schedules:
            keyboard.append([
                InlineKeyboardButton(text=f"🗓 {sc['title'][:26]}", callback_data=f"sched_get:{sc['id']}"),
                InlineKeyboardButton(text="🗑 حذف", callback_data=f"adm_sched_del:{sc['id']}")
            ])
    keyboard.append([InlineKeyboardButton(text="➕ رفع جدول دراسي جديد", callback_data="upload_opt_schedule")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_books_schedules")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_sched_del:"))
async def cb_adm_sched_del(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    sched_id = int(callback.data.split(":")[1])
    await delete_schedule(sched_id)
    await callback.answer("🗑 تم حذف الجدول بنجاح.", show_alert=True)
    await cb_adm_schedules_list(callback)

# ==========================================
# إدارة الفيديوهات (Videos Management Hub)
# ==========================================
@router.callback_query(F.data == "admin_videos_hub")
async def cb_admin_videos_hub(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    from database import get_db
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT v.*, l.name as lecture_name, s.name as subject_name
            FROM videos v
            JOIN lectures l ON v.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            ORDER BY v.created_at DESC LIMIT 20;
        """)
        rows = await cursor.fetchall()
        recent_videos = [dict(r) for r in rows]

    text = (
        "🎥 <b>إدارة الفيديوهات والمحاضرات المصورة:</b>\n\n"
        f"أحدث الفيديوهات المسجلة في النظام ({len(recent_videos)}):\n"
    )
    keyboard = []
    if not recent_videos:
        text += "<i>لا توجد فيديوهات مرفوعة حتى الآن.</i>\n"
    else:
        for vid in recent_videos:
            vis = "👁" if not vid.get("is_hidden") else "🙈"
            title = f"{vis} {vid['title']}"
            keyboard.append([
                InlineKeyboardButton(text=f"🎬 {title[:25]}", callback_data=f"video_get:{vid['id']}"),
                InlineKeyboardButton(text="إخفاء/إظهار", callback_data=f"adm_vid_toggle:{vid['id']}"),
                InlineKeyboardButton(text="🗑 حذف", callback_data=f"adm_vid_del:{vid['id']}")
            ])

    keyboard.append([InlineKeyboardButton(text="➕ رفع أو إضافة فيديو جديد", callback_data="upload_opt_video")])
    keyboard.append([InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_vid_toggle:"))
async def cb_adm_vid_toggle(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    vid_id = int(callback.data.split(":")[1])
    await toggle_video_hidden(vid_id)
    await callback.answer("✅ تم تغيير حالة إظهار/إخفاء الفيديو.")
    await cb_admin_videos_hub(callback)

@router.callback_query(F.data.startswith("adm_vid_del:"))
async def cb_adm_vid_del(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    vid_id = int(callback.data.split(":")[1])
    await delete_video(vid_id)
    await callback.answer("🗑 تم حذف الفيديو بنجاح.", show_alert=True)
    await cb_admin_videos_hub(callback)
