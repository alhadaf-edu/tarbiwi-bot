from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    get_study_days, get_day_by_id, get_subjects_by_day, get_subject_by_id,
    get_specializations, get_specialization_by_id, get_lectures, get_lecture_by_id,
    add_lecture, add_file, add_video, add_book, add_schedule, add_subject_suggestion,
    CATEGORY_NAMES, CATEGORY_ICONS
)
from utils.states import (
    UploadBookStates, UploadScheduleStates, SuggestSubjectStates,
    AddLectureStates, UploadVideoStates, UploadFileStates
)
from utils.security import is_safe_file_name, is_file_size_acceptable, is_valid_url
from keyboards.upload_kb import (
    get_upload_menu_keyboard, get_consecutive_upload_keyboard,
    get_confirm_keyboard, get_skip_or_cancel_keyboard, get_category_selection_keyboard
)
from keyboards.main_kb import get_cancel_keyboard
from middlewares.auth import check_user_membership
from services.archive import archive_document, archive_video
from services.notifier import notify_new_content

router = Router(name="upload")

# --- Upload Menu Entry ---
@router.callback_query(F.data == "upload_main")
async def cb_upload_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Check group membership if required
    is_member = await check_user_membership(callback.bot, callback.from_user.id)
    if not is_member:
        await callback.answer(
            "⚠️ عذراً! رفع المحتوى متاح لأعضاء مجموعة دبلومة التأهيل التربوي فقط. يرجى الانضمام للمجموعة أولاً.",
            show_alert=True
        )
        return

    text = (
        "📤 <b>مشاركة محتوى تعليمي جديد:</b>\n\n"
        "أهلاً بك زميلنا العزيز! يمكنك المساهمة في إثراء محتوى الدبلومة من خلال الخيارات التالية:\n\n"
        "1️⃣ <b>إضافة كتاب دراسي:</b> كتب ومراجع المنهج.\n"
        "2️⃣ <b>إضافة جدول دراسي:</b> جداول المواعيد والمحاضرات.\n"
        "3️⃣ <b>اقتراح مادة جديدة:</b> إرسال اقتراح لمادة دراسية للمشرفين.\n"
        "4️⃣ <b>إضافة محاضرة جديدة:</b> فتح محاضرة جديدة لأي مادة وتخصص.\n"
        "5️⃣ <b>رفع فيديو لمحاضرة:</b> فيديو مباشر أو رابط يوتيوب/سحابي.\n"
        "6️⃣ <b>رفع ملف لمحاضرة:</b> ملخصات AI، شرح يدوي، أو PowerPoint الدكتور.\n\n"
        "اختر نوع المحتوى الذي ترغب في رفعه 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_upload_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==========================================
# 1. إضافة كتاب دراسي
# ==========================================
@router.callback_query(F.data == "upload_opt_book")
@router.callback_query(F.data == "start_upload_book")
async def start_book_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UploadBookStates.waiting_for_title)
    text = (
        "📖 <b>إضافة كتاب دراسي جديد:</b>\n\n"
        "الخطوة 1 من 4: أرسل <b>اسم الكتاب أو المرجع</b>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(UploadBookStates.waiting_for_title)
async def book_title_received(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(book_title=title)
    await state.set_state(UploadBookStates.waiting_for_file)
    text = (
        f"📖 <b>اسم الكتاب:</b> {title}\n\n"
        "الخطوة 2 من 4: الآن أرسل <b>ملف الكتاب (PDF أو مستند)</b>:"
    )
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadBookStates.waiting_for_file, F.document)
async def book_file_received(message: Message, state: FSMContext):
    doc = message.document
    safe, err = is_safe_file_name(doc.file_name)
    if not safe:
        await message.answer(f"❌ {err}\nيرجى إرسال ملف بصيغة صحيحة مثل PDF.", reply_markup=get_cancel_keyboard())
        return

    size_ok, size_err = is_file_size_acceptable(doc.file_size or 0)
    if not size_ok:
        await message.answer(f"❌ {size_err}", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(
        file_id=doc.file_id,
        file_name=doc.file_name or "Book.pdf",
        file_size=doc.file_size or 0
    )
    await state.set_state(UploadBookStates.waiting_for_description)
    text = (
        "✅ تم استلام الملف بنجاح!\n\n"
        "الخطوة 3 من 4: أرسل <b>وصفاً مختصراً للكتاب</b> (اختياري)، أو اضغط على «تخطي»:"
    )
    await message.answer(text, reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(UploadBookStates.waiting_for_description, F.data == "skip_step")
async def book_skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await show_book_summary(callback.message, state)
    await callback.answer()

@router.message(UploadBookStates.waiting_for_description)
async def book_desc_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await show_book_summary(message, state)

async def show_book_summary(msg_or_cb, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UploadBookStates.confirm_upload)
    text = (
        "📋 <b>مراجعة بيانات الكتاب قبل النشر:</b>\n\n"
        f"📖 <b>اسم الكتاب:</b> {data['book_title']}\n"
        f"📄 <b>الملف:</b> {data.get('file_name', 'مستند')}\n"
        f"📝 <b>الوصف:</b> {data.get('description') or 'لا يوجد'}\n\n"
        "اضغط على «تأكيد ونشر الآن» لحفظ الكتاب في المكتبة:"
    )
    await msg_or_cb.answer(text, reply_markup=get_confirm_keyboard("confirm_book_publish"), parse_mode="HTML")

@router.callback_query(UploadBookStates.confirm_upload, F.data == "confirm_book_publish")
async def confirm_book_publish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user

    # Archive file to channel
    caption = f"📚 كتاب: {data['book_title']}\nبواسطة: {user.full_name}"
    arch_msg_id, arch_file_id = await archive_document(
        callback.bot,
        data["file_id"],
        caption
    )

    final_file_id = arch_file_id or data["file_id"]

    await add_book(
        title=data["book_title"],
        telegram_file_id=final_file_id,
        uploader_id=user.id,
        uploader_name=user.full_name,
        description=data.get("description", ""),
        archive_message_id=arch_msg_id
    )

    # Broadcast notification to group
    await notify_new_content(
        bot=callback.bot,
        content_type="كتاب دراسي 📖",
        title=data["book_title"],
        uploader_name=user.full_name
    )

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 تصفح الكتب", callback_data="books_list:0")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]
    ])
    await callback.message.edit_text("🎉 <b>تم نشر الكتاب في المكتبة بنجاح!</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 2. إضافة جدول دراسي
# ==========================================
@router.callback_query(F.data == "upload_opt_schedule")
async def start_schedule_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UploadScheduleStates.waiting_for_title)
    text = (
        "🗓 <b>إضافة جدول دراسي:</b>\n\n"
        "الخطوة 1 من 3: أرسل <b>عنوان الجدول</b> (مثال: جدول المحاضرات المحدث لشهر نوفمبر):"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(UploadScheduleStates.waiting_for_title)
async def sched_title_received(message: Message, state: FSMContext):
    await state.update_data(sched_title=message.text.strip())
    await state.set_state(UploadScheduleStates.waiting_for_file)
    text = "الخطوة 2 من 3: أرسل <b>ملف الجدول أو صورته</b>:"
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadScheduleStates.waiting_for_file, F.document | F.photo)
async def sched_file_received(message: Message, state: FSMContext):
    if message.document:
        doc = message.document
        safe, err = is_safe_file_name(doc.file_name)
        if not safe:
            await message.answer(f"❌ {err}", reply_markup=get_cancel_keyboard())
            return
        file_id = doc.file_id
    else:
        file_id = message.photo[-1].file_id

    await state.update_data(file_id=file_id)
    await state.set_state(UploadScheduleStates.waiting_for_description)
    await message.answer("الخطوة 3 من 3: أرسل وصفاً إضافياً أو اضغط «تخطي»:", reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(UploadScheduleStates.waiting_for_description, F.data == "skip_step")
async def sched_skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await confirm_schedule_save(callback.message, callback.from_user, state, callback.bot)
    await callback.answer()

@router.message(UploadScheduleStates.waiting_for_description)
async def sched_desc_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await confirm_schedule_save(message, message.from_user, state, message.bot)

async def confirm_schedule_save(msg, user, state: FSMContext, bot):
    data = await state.get_data()
    arch_msg_id, arch_file_id = await archive_document(bot, data["file_id"], f"🗓 جدول: {data['sched_title']}")
    final_file_id = arch_file_id or data["file_id"]

    await add_schedule(
        title=data["sched_title"],
        telegram_file_id=final_file_id,
        uploader_id=user.id,
        uploader_name=user.full_name,
        description=data.get("description", ""),
        archive_message_id=arch_msg_id
    )

    await notify_new_content(
        bot=bot,
        content_type="جدول دراسي 🗓",
        title=data["sched_title"],
        uploader_name=user.full_name
    )

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]])
    await msg.answer("🎉 <b>تم حفظ ونشر الجدول بنجاح!</b>", reply_markup=kb, parse_mode="HTML")

# ==========================================
# 3. اقتراح مادة جديدة
# ==========================================
@router.callback_query(F.data == "upload_opt_suggest_subject")
async def start_suggest_subject(callback: CallbackQuery, state: FSMContext):
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 {d['name']}", callback_data=f"sugg_day:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(SuggestSubjectStates.waiting_for_day)
    text = "💡 <b>اقتراح مادة جديدة:</b>\n\nالخطوة 1 من 3: اختر اليوم الدراسي للمادة المقترحة:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(SuggestSubjectStates.waiting_for_day, F.data.startswith("sugg_day:"))
async def sugg_day_picked(callback: CallbackQuery, state: FSMContext):
    day_id = int(callback.data.split(":")[1])
    day = await get_day_by_id(day_id)
    await state.update_data(day_id=day_id, day_name=day['name'])
    await state.set_state(SuggestSubjectStates.waiting_for_name)
    text = (
        f"📅 اليوم المختار: <b>{day['name']}</b>\n\n"
        "الخطوة 2 من 3: أرسل <b>اسم المادة المقترحة</b>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(SuggestSubjectStates.waiting_for_name)
async def sugg_name_received(message: Message, state: FSMContext):
    await state.update_data(subject_name=message.text.strip())
    await state.set_state(SuggestSubjectStates.waiting_for_doctor)
    text = "الخطوة 3 من 3: أرسل <b>اسم الدكتور / عضو هيئة التدريس</b> (أو اضغط «تخطي»):"
    await message.answer(text, reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(SuggestSubjectStates.waiting_for_doctor, F.data == "skip_step")
async def sugg_skip_doc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(doctor_name="")
    await confirm_suggestion_step(callback.message, callback.from_user, state)
    await callback.answer()

@router.message(SuggestSubjectStates.waiting_for_doctor)
async def sugg_doc_received(message: Message, state: FSMContext):
    await state.update_data(doctor_name=message.text.strip())
    await confirm_suggestion_step(message, message.from_user, state)

async def confirm_suggestion_step(msg, user, state: FSMContext):
    data = await state.get_data()
    await add_subject_suggestion(
        day_id=data["day_id"],
        name=data["subject_name"],
        doctor_name=data.get("doctor_name", ""),
        user_id=user.id,
        user_name=user.full_name
    )
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]])
    text = (
        "✅ <b>تم استلام اقتراح المادة بنجاح!</b>\n\n"
        f"📅 <b>اليوم:</b> {data['day_name']}\n"
        f"📖 <b>المادة:</b> {data['subject_name']}\n"
        f"👨‍🏫 <b>الدكتور:</b> {data.get('doctor_name') or 'غير محدد'}\n\n"
        "سيقوم المشرفون بمراجعة الاقتراح وإضافته للجدول بعد التدقيق."
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

# ==========================================
# 4. إضافة محاضرة جديدة
# ==========================================
@router.callback_query(F.data == "upload_opt_lecture")
async def start_add_lecture(callback: CallbackQuery, state: FSMContext):
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 {d['name']}", callback_data=f"lec_day:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(AddLectureStates.waiting_for_day)
    text = "🎓 <b>إضافة محاضرة جديدة:</b>\n\nالخطوة 1: اختر اليوم الدراسي:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("quick_add_lec:"))
async def quick_add_lecture(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    subject_id = int(parts[1])
    spec_id = int(parts[2]) if int(parts[2]) > 0 else None

    subject = await get_subject_by_id(subject_id)
    await state.update_data(
        subject_id=subject_id,
        subject_name=subject['name'],
        spec_id=spec_id
    )
    await state.set_state(AddLectureStates.waiting_for_lecture_name)
    text = (
        f"📖 المادة: <b>{subject['name']}</b>\n\n"
        "أرسل الآن <b>اسم المحاضرة أو رقمها</b> (مثال: المحاضرة الخامسة):"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AddLectureStates.waiting_for_day, F.data.startswith("lec_day:"))
async def add_lec_day_picked(callback: CallbackQuery, state: FSMContext):
    day_id = int(callback.data.split(":")[1])
    subjects = await get_subjects_by_day(day_id)

    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(text=f"📖 {s['name']}", callback_data=f"lec_subj:{s['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(AddLectureStates.waiting_for_subject)
    await callback.message.edit_text("الخطوة 2: اختر المادة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AddLectureStates.waiting_for_subject, F.data.startswith("lec_subj:"))
async def add_lec_subj_picked(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    subject = await get_subject_by_id(subject_id)
    await state.update_data(subject_id=subject_id, subject_name=subject['name'])

    if subject.get("has_specializations"):
        specs = await get_specializations(subject_id)
        keyboard = []
        for sp in specs:
            keyboard.append([InlineKeyboardButton(text=f"🎯 {sp['name']}", callback_data=f"lec_spec:{sp['id']}")])
        keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
        await state.set_state(AddLectureStates.waiting_for_spec)
        await callback.message.edit_text("🎯 اختر التخصص لهذه المحاضرة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(spec_id=None)
    await state.set_state(AddLectureStates.waiting_for_lecture_name)
    await callback.message.edit_text("أرسل الآن <b>اسم المحاضرة أو رقمها</b> (مثال: المحاضرة الرابعة):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AddLectureStates.waiting_for_spec, F.data.startswith("lec_spec:"))
async def add_lec_spec_picked(callback: CallbackQuery, state: FSMContext):
    spec_id = int(callback.data.split(":")[1])
    await state.update_data(spec_id=spec_id)
    await state.set_state(AddLectureStates.waiting_for_lecture_name)
    await callback.message.edit_text("أرسل الآن <b>اسم المحاضرة أو رقمها</b> (مثال: المحاضرة الثانية):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(AddLectureStates.waiting_for_lecture_name)
async def add_lec_name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    lec_name = message.text.strip()
    lec_id = await add_lecture(
        subject_id=data["subject_id"],
        name=lec_name,
        specialization_id=data.get("spec_id")
    )
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 فتح المحاضرة الآن", callback_data=f"lec_view:{lec_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]
    ])
    await message.answer(f"🎉 <b>تم إنشاء ({lec_name}) بنجاح!</b>\nيمكنك الآن رفع الفيديوهات والملفات إليها مباشرة.", reply_markup=kb, parse_mode="HTML")

# ==========================================
# 5. رفع فيديو لمحاضرة
# ==========================================
@router.callback_query(F.data == "upload_opt_video")
async def start_video_upload(callback: CallbackQuery, state: FSMContext):
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 {d['name']}", callback_data=f"vid_day:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(UploadVideoStates.waiting_for_day)
    await callback.message.edit_text("🎥 <b>رفع فيديو لمحاضرة:</b>\n\nالخطوة 1: اختر اليوم الدراسي:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("quick_upload_video:"))
async def quick_upload_video(callback: CallbackQuery, state: FSMContext):
    lecture_id = int(callback.data.split(":")[1])
    lecture = await get_lecture_by_id(lecture_id)
    await state.update_data(
        lecture_id=lecture_id,
        lecture_name=lecture['name'],
        subject_name=lecture['subject_name'],
        day_name=lecture['day_name'],
        spec_id=lecture.get('specialization_id'),
        spec_name=lecture.get('spec_name')
    )
    await state.set_state(UploadVideoStates.waiting_for_title)
    text = (
        f"🎥 <b>إضافة فيديو لـ ({lecture['name']}):</b>\n\n"
        "أرسل <b>عنوان الفيديو</b> (مثال: شرح الجزء الأول من المحاضرة):"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadVideoStates.waiting_for_day, F.data.startswith("vid_day:"))
async def vid_day_picked(callback: CallbackQuery, state: FSMContext):
    day_id = int(callback.data.split(":")[1])
    day = await get_day_by_id(day_id)
    await state.update_data(day_id=day_id, day_name=day['name'])
    subjects = await get_subjects_by_day(day_id)
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(text=f"📖 {s['name']}", callback_data=f"vid_subj:{s['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
    await state.set_state(UploadVideoStates.waiting_for_subject)
    await callback.message.edit_text("الخطوة 2: اختر المادة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadVideoStates.waiting_for_subject, F.data.startswith("vid_subj:"))
async def vid_subj_picked(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    subject = await get_subject_by_id(subject_id)
    await state.update_data(subject_id=subject_id, subject_name=subject['name'])

    if subject.get("has_specializations"):
        specs = await get_specializations(subject_id)
        keyboard = []
        for sp in specs:
            keyboard.append([InlineKeyboardButton(text=f"🎯 {sp['name']}", callback_data=f"vid_spec:{sp['id']}")])
        keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
        await state.set_state(UploadVideoStates.waiting_for_spec)
        await callback.message.edit_text("الخطوة 3: اختر التخصص:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(spec_id=None, spec_name=None)
    lectures = await get_lectures(subject_id)
    if not lectures:
        await callback.answer("لا توجد محاضرات في هذه المادة. أضف محاضرة أولاً.", show_alert=True)
        return
    keyboard = []
    for l in lectures:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {l['name']}", callback_data=f"vid_lec:{l['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
    await state.set_state(UploadVideoStates.waiting_for_lecture)
    await callback.message.edit_text("الخطوة 3: اختر المحاضرة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadVideoStates.waiting_for_spec, F.data.startswith("vid_spec:"))
async def vid_spec_picked(callback: CallbackQuery, state: FSMContext):
    spec_id = int(callback.data.split(":")[1])
    spec = await get_specialization_by_id(spec_id)
    data = await state.get_data()
    await state.update_data(spec_id=spec_id, spec_name=spec['name'])
    lectures = await get_lectures(data["subject_id"], specialization_id=spec_id)
    if not lectures:
        await callback.answer("لا توجد محاضرات في هذا التخصص. أضف محاضرة أولاً.", show_alert=True)
        return
    keyboard = []
    for l in lectures:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {l['name']}", callback_data=f"vid_lec:{l['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
    await state.set_state(UploadVideoStates.waiting_for_lecture)
    await callback.message.edit_text("الخطوة 4: اختر المحاضرة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadVideoStates.waiting_for_lecture, F.data.startswith("vid_lec:"))
async def vid_lec_picked(callback: CallbackQuery, state: FSMContext):
    lec_id = int(callback.data.split(":")[1])
    lec = await get_lecture_by_id(lec_id)
    await state.update_data(lecture_id=lec_id, lecture_name=lec['name'])
    await state.set_state(UploadVideoStates.waiting_for_title)
    await callback.message.edit_text("أرسل الآن <b>عنوان الفيديو</b> (مثال: تسجيل محاضرة الأسبوع):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(UploadVideoStates.waiting_for_title)
async def vid_title_received(message: Message, state: FSMContext):
    await state.update_data(video_title=message.text.strip())
    await state.set_state(UploadVideoStates.waiting_for_video_content)
    text = (
        f"🎬 <b>عنوان الفيديو:</b> {message.text.strip()}\n\n"
        "أرسل الآن <b>ملف الفيديو مباشرة</b> إلى المحادثة أو أرسل <b>رابط الفيديو الخارجي</b> (YouTube / Drive / Telegram link):"
    )
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadVideoStates.waiting_for_video_content, F.video | F.document)
async def vid_file_received(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
    else:
        doc = message.document
        safe, err = is_safe_file_name(doc.file_name)
        if not safe:
            await message.answer(f"❌ {err}", reply_markup=get_cancel_keyboard())
            return
        file_id = doc.file_id

    await state.update_data(video_type="telegram_video", file_id=file_id, external_url=None)
    await state.set_state(UploadVideoStates.waiting_for_description)
    await message.answer("أرسل وصفاً للفيديو أو اضغط «تخطي»:", reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadVideoStates.waiting_for_video_content, F.text)
async def vid_url_received(message: Message, state: FSMContext):
    url = message.text.strip()
    if not is_valid_url(url):
        await message.answer("⚠️ يرجى إرسال رابط صحيح (يبدأ بـ http:// أو https://) أو رفع ملف فيديو.", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(video_type="external_url", file_id=None, external_url=url)
    await state.set_state(UploadVideoStates.waiting_for_description)
    await message.answer("أرسل وصفاً للفيديو أو اضغط «تخطي»:", reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(UploadVideoStates.waiting_for_description, F.data == "skip_step")
async def vid_skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await show_video_summary(callback.message, state)
    await callback.answer()

@router.message(UploadVideoStates.waiting_for_description)
async def vid_desc_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await show_video_summary(message, state)

async def show_video_summary(msg_or_cb, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UploadVideoStates.confirm_upload)
    spec_part = f" ⬅️ {data['spec_name']}" if data.get('spec_name') else ""
    path = f"{data.get('day_name','')} ⬅️ {data.get('subject_name','')} {spec_part} ⬅️ {data.get('lecture_name','')}"

    text = (
        "📋 <b>مراجعة بيانات الفيديو قبل النشر:</b>\n\n"
        f"🎬 <b>عنوان الفيديو:</b> {data['video_title']}\n"
        f"📍 <b>المسار:</b> {path}\n"
        f"نوع المحتوى: {'ملف فيديو في تيليجرام' if data['video_type']=='telegram_video' else 'رابط خارجي'}\n"
        f"📝 <b>الوصف:</b> {data.get('description') or 'لا يوجد'}\n\n"
        "اضغط على «تأكيد ونشر الآن»:"
    )
    await msg_or_cb.answer(text, reply_markup=get_confirm_keyboard("confirm_video_publish"), parse_mode="HTML")

@router.callback_query(UploadVideoStates.confirm_upload, F.data == "confirm_video_publish")
async def confirm_video_publish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user

    arch_msg_id = None
    final_file_id = data.get("file_id")

    if data["video_type"] == "telegram_video" and final_file_id:
        arch_msg_id, arch_file_id = await archive_video(
            callback.bot,
            final_file_id,
            f"🎬 فيديو: {data['video_title']}\nبواسطة: {user.full_name}"
        )
        if arch_file_id:
            final_file_id = arch_file_id

    await add_video(
        lecture_id=data["lecture_id"],
        title=data["video_title"],
        video_type=data["video_type"],
        uploader_id=user.id,
        uploader_name=user.full_name,
        specialization_id=data.get("spec_id"),
        description=data.get("description", ""),
        telegram_file_id=final_file_id,
        external_url=data.get("external_url"),
        archive_message_id=arch_msg_id
    )

    await notify_new_content(
        bot=callback.bot,
        content_type="فيديو محاضرة 🎥",
        title=data["video_title"],
        uploader_name=user.full_name,
        day_name=data.get("day_name"),
        subject_name=data.get("subject_name"),
        lecture_name=data.get("lecture_name"),
        spec_name=data.get("spec_name")
    )

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 عرض فيديوهات المحاضرة", callback_data=f"lec_videos:{data['lecture_id']}:0")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]
    ])
    await callback.message.edit_text("🎉 <b>تم نشر الفيديو بنجاح!</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 6. رفع ملف لمحاضرة موجودة (الأهم: تعدد الملفات ودعم الرفع المتتالي)
# ==========================================
@router.callback_query(F.data == "upload_opt_file")
async def start_file_upload(callback: CallbackQuery, state: FSMContext):
    days = await get_study_days()
    keyboard = []
    for d in days:
        keyboard.append([InlineKeyboardButton(text=f"📅 {d['name']}", callback_data=f"uf_day:{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(UploadFileStates.waiting_for_day)
    text = (
        "📁 <b>رفع ملف لمحاضرة موجودة:</b>\n\n"
        "الخطوة 1 من 6: اختر اليوم الدراسي للمادة:"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# Shortcut for uploading directly to a category from inside lecture view
@router.callback_query(F.data.startswith("quick_upload_file:"))
async def quick_upload_file(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    lecture_id = int(parts[1])
    category = parts[2]
    lecture = await get_lecture_by_id(lecture_id)

    await state.update_data(
        day_id=lecture.get('day_id'),
        day_name=lecture['day_name'],
        subject_id=lecture['subject_id'],
        subject_name=lecture['subject_name'],
        spec_id=lecture.get('specialization_id'),
        spec_name=lecture.get('spec_name'),
        lecture_id=lecture_id,
        lecture_name=lecture['name'],
        category=category
    )

    cat_name = CATEGORY_NAMES.get(category, category)
    await state.set_state(UploadFileStates.waiting_for_file_name)
    text = (
        f"📂 <b>رفع ملف جديد:</b>\n"
        f"المحاضرة: <b>{lecture['name']}</b>\n"
        f"التصنيف: <b>{cat_name}</b>\n\n"
        "أرسل الآن <b>اسم الملف</b> (مثال: ملخص الدرس الأول):"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadFileStates.waiting_for_day, F.data.startswith("uf_day:"))
async def uf_day_picked(callback: CallbackQuery, state: FSMContext):
    day_id = int(callback.data.split(":")[1])
    day = await get_day_by_id(day_id)
    await state.update_data(day_id=day_id, day_name=day['name'])
    subjects = await get_subjects_by_day(day_id)

    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(text=f"📖 {s['name']}", callback_data=f"uf_subj:{s['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])

    await state.set_state(UploadFileStates.waiting_for_subject)
    await callback.message.edit_text("الخطوة 2 من 6: اختر المادة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadFileStates.waiting_for_subject, F.data.startswith("uf_subj:"))
async def uf_subj_picked(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    subject = await get_subject_by_id(subject_id)
    await state.update_data(subject_id=subject_id, subject_name=subject['name'])

    if subject.get("has_specializations"):
        specs = await get_specializations(subject_id)
        keyboard = []
        for sp in specs:
            keyboard.append([InlineKeyboardButton(text=f"🎯 {sp['name']}", callback_data=f"uf_spec:{sp['id']}")])
        keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
        await state.set_state(UploadFileStates.waiting_for_spec)
        await callback.message.edit_text("الخطوة 3: اختر التخصص:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(spec_id=None, spec_name=None)
    lectures = await get_lectures(subject_id)
    if not lectures:
        await callback.answer("لا توجد محاضرات في هذه المادة بعد. يرجى إضافة محاضرة أولاً.", show_alert=True)
        return

    keyboard = []
    for l in lectures:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {l['name']}", callback_data=f"uf_lec:{l['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
    await state.set_state(UploadFileStates.waiting_for_lecture)
    await callback.message.edit_text("الخطوة 3 من 6: اختر المحاضرة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadFileStates.waiting_for_spec, F.data.startswith("uf_spec:"))
async def uf_spec_picked(callback: CallbackQuery, state: FSMContext):
    spec_id = int(callback.data.split(":")[1])
    spec = await get_specialization_by_id(spec_id)
    data = await state.get_data()
    await state.update_data(spec_id=spec_id, spec_name=spec['name'])

    lectures = await get_lectures(data["subject_id"], specialization_id=spec_id)
    if not lectures:
        await callback.answer("لا توجد محاضرات في هذا التخصص. أضف محاضرة أولاً.", show_alert=True)
        return

    keyboard = []
    for l in lectures:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {l['name']}", callback_data=f"uf_lec:{l['id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="home")])
    await state.set_state(UploadFileStates.waiting_for_lecture)
    await callback.message.edit_text("الخطوة 4: اختر المحاضرة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadFileStates.waiting_for_lecture, F.data.startswith("uf_lec:"))
async def uf_lec_picked(callback: CallbackQuery, state: FSMContext):
    lec_id = int(callback.data.split(":")[1])
    lec = await get_lecture_by_id(lec_id)
    await state.update_data(lecture_id=lec_id, lecture_name=lec['name'])
    await state.set_state(UploadFileStates.waiting_for_category)
    await callback.message.edit_text("الخطوة 4 من 6: اختر <b>تصنيف الملف</b>:", reply_markup=get_category_selection_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(UploadFileStates.waiting_for_category, F.data.startswith("pick_cat:"))
async def uf_cat_picked(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    cat_name = CATEGORY_NAMES.get(category, category)
    await state.set_state(UploadFileStates.waiting_for_file_name)
    text = (
        f"التصنيف: <b>{cat_name}</b>\n\n"
        "الخطوة 5 من 6: أرسل <b>اسم الملف</b> (مثال: ملخص شامل للمحاضرة الأولى):"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(UploadFileStates.waiting_for_file_name)
async def uf_name_received(message: Message, state: FSMContext):
    await state.update_data(custom_file_name=message.text.strip())
    await state.set_state(UploadFileStates.waiting_for_file_document)
    text = "الخطوة 6 من 6: الآن أرسل <b>الملف</b> (PDF أو PowerPoint أو Word أو صورة):"
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadFileStates.waiting_for_file_document, F.document | F.photo)
async def uf_doc_received(message: Message, state: FSMContext):
    if message.document:
        doc = message.document
        safe, err = is_safe_file_name(doc.file_name)
        if not safe:
            await message.answer(f"❌ {err}", reply_markup=get_cancel_keyboard())
            return
        size_ok, size_err = is_file_size_acceptable(doc.file_size or 0)
        if not size_ok:
            await message.answer(f"❌ {size_err}", reply_markup=get_cancel_keyboard())
            return
        file_id = doc.file_id
        file_size = doc.file_size or 0
        file_type = "document"
    else:
        file_id = message.photo[-1].file_id
        file_size = 0
        file_type = "photo"

    await state.update_data(file_id=file_id, file_size=file_size, file_type=file_type)
    await state.set_state(UploadFileStates.waiting_for_description)
    await message.answer("أرسل وصفاً للملف (اختياري) أو اضغط «تخطي»:", reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(UploadFileStates.waiting_for_description, F.data == "skip_step")
async def uf_skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await show_file_summary(callback.message, state)
    await callback.answer()

@router.message(UploadFileStates.waiting_for_description)
async def uf_desc_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await show_file_summary(message, state)

async def show_file_summary(msg_or_cb, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UploadFileStates.confirm_upload)
    cat_name = CATEGORY_NAMES.get(data['category'], data['category'])
    spec_part = f" ⬅️ {data['spec_name']}" if data.get('spec_name') else ""
    path = f"{data.get('day_name','')} ⬅️ {data.get('subject_name','')} {spec_part} ⬅️ {data.get('lecture_name','')}"

    text = (
        "📋 <b>مراجعة بيانات الملف قبل النشر:</b>\n\n"
        f"📄 <b>اسم الملف:</b> {data['custom_file_name']}\n"
        f"📂 <b>التصنيف:</b> {cat_name}\n"
        f"📍 <b>المسار:</b> {path}\n"
        f"📝 <b>الوصف:</b> {data.get('description') or 'لا يوجد'}\n\n"
        "اضغط على «تأكيد ونشر الآن» لحفظ الملف مباشرة في المكتبة:"
    )
    await msg_or_cb.answer(text, reply_markup=get_confirm_keyboard("confirm_file_publish"), parse_mode="HTML")

@router.callback_query(UploadFileStates.confirm_upload, F.data == "confirm_file_publish")
async def confirm_file_publish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user

    cat_name = CATEGORY_NAMES.get(data['category'], data['category'])

    # Archive to channel
    caption = f"📄 {data['custom_file_name']}\nتصنيف: {cat_name}\nبواسطة: {user.full_name}"
    arch_msg_id, arch_file_id = await archive_document(
        callback.bot,
        data["file_id"],
        caption
    )
    final_file_id = arch_file_id or data["file_id"]

    # CRITICAL: add_file creates an independent row, supporting unlimited files per category!
    await add_file(
        lecture_id=data["lecture_id"],
        category=data["category"],
        file_name=data["custom_file_name"],
        telegram_file_id=final_file_id,
        uploader_id=user.id,
        uploader_name=user.full_name,
        specialization_id=data.get("spec_id"),
        description=data.get("description", ""),
        archive_message_id=arch_msg_id,
        file_type=data.get("file_type", "document"),
        file_size=data.get("file_size", 0)
    )

    # Notify main group
    await notify_new_content(
        bot=callback.bot,
        content_type=f"ملف محاضرة ({cat_name}) 📁",
        title=data["custom_file_name"],
        uploader_name=user.full_name,
        day_name=data.get("day_name"),
        subject_name=data.get("subject_name"),
        lecture_name=data.get("lecture_name"),
        spec_name=data.get("spec_name"),
        category_name=cat_name
    )

    # Exact format required by requirement 7.7
    success_text = (
        "✅ <b>تم نشر الملف بنجاح!</b>\n\n"
        f"📖 <b>المادة:</b> {data.get('subject_name')}\n"
        f"🎓 <b>المحاضرة:</b> {data.get('lecture_name')}\n"
        f"📂 <b>التصنيف:</b> {cat_name}\n"
        f"📄 <b>اسم الملف:</b> {data.get('custom_file_name')}\n\n"
        "يمكنك رفع ملف آخر لنفس المحاضرة والتصنيف مباشرة بضغطة زر 👇"
    )

    kb = get_consecutive_upload_keyboard(data["lecture_id"], data["category"])
    await callback.message.edit_text(success_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 7.7 رفع ملفات متعددة متتالية (الاحتفاظ بالمسار والطلب فقط للاسم والملف)
# ==========================================
@router.callback_query(F.data.startswith("consec_upload:"))
async def start_consecutive_upload(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    lecture_id = int(parts[1])
    category = parts[2]
    lecture = await get_lecture_by_id(lecture_id)

    # Keep all context from previous upload!
    await state.update_data(
        day_name=lecture['day_name'],
        subject_name=lecture['subject_name'],
        spec_id=lecture.get('specialization_id'),
        spec_name=lecture.get('spec_name'),
        lecture_id=lecture_id,
        lecture_name=lecture['name'],
        category=category
    )

    cat_name = CATEGORY_NAMES.get(category, category)
    await state.set_state(UploadFileStates.waiting_for_next_file_name)
    text = (
        f"📤 <b>رفع ملف آخر لنفس المحاضرة:</b>\n"
        f"🎓 <b>المحاضرة:</b> {lecture['name']}\n"
        f"📂 <b>التصنيف:</b> {cat_name}\n\n"
        "1️⃣ أرسل <b>اسم الملف الجديد</b>:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(UploadFileStates.waiting_for_next_file_name)
async def next_file_name_received(message: Message, state: FSMContext):
    await state.update_data(custom_file_name=message.text.strip())
    await state.set_state(UploadFileStates.waiting_for_next_file_document)
    text = "2️⃣ الآن أرسل <b>الملف</b>:"
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@router.message(UploadFileStates.waiting_for_next_file_document, F.document | F.photo)
async def next_file_doc_received(message: Message, state: FSMContext):
    if message.document:
        doc = message.document
        safe, err = is_safe_file_name(doc.file_name)
        if not safe:
            await message.answer(f"❌ {err}", reply_markup=get_cancel_keyboard())
            return
        file_id = doc.file_id
        file_size = doc.file_size or 0
        file_type = "document"
    else:
        file_id = message.photo[-1].file_id
        file_size = 0
        file_type = "photo"

    await state.update_data(file_id=file_id, file_size=file_size, file_type=file_type)
    await state.set_state(UploadFileStates.waiting_for_next_description)
    await message.answer("3️⃣ أرسل وصفاً للملف (اختياري) أو اضغط «تخطي»:", reply_markup=get_skip_or_cancel_keyboard(), parse_mode="HTML")

@router.callback_query(UploadFileStates.waiting_for_next_description, F.data == "skip_step")
async def next_file_skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await show_next_file_summary(callback.message, state)
    await callback.answer()

@router.message(UploadFileStates.waiting_for_next_description)
async def next_file_desc_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await show_next_file_summary(message, state)

async def show_next_file_summary(msg_or_cb, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UploadFileStates.confirm_next_upload)
    cat_name = CATEGORY_NAMES.get(data['category'], data['category'])

    text = (
        "📋 <b>تأكيد نشر الملف المتتالي:</b>\n\n"
        f"📄 <b>اسم الملف:</b> {data['custom_file_name']}\n"
        f"📂 <b>التصنيف:</b> {cat_name}\n"
        f"🎓 <b>المحاضرة:</b> {data['lecture_name']}\n"
        f"📝 <b>الوصف:</b> {data.get('description') or 'لا يوجد'}\n\n"
        "اضغط على «تأكيد ونشر الآن»:"
    )
    await msg_or_cb.answer(text, reply_markup=get_confirm_keyboard("confirm_next_file_publish"), parse_mode="HTML")

@router.callback_query(UploadFileStates.confirm_next_upload, F.data == "confirm_next_file_publish")
async def confirm_next_file_publish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    cat_name = CATEGORY_NAMES.get(data['category'], data['category'])

    # Archive to channel
    caption = f"📄 {data['custom_file_name']}\nتصنيف: {cat_name}\nبواسطة: {user.full_name}"
    arch_msg_id, arch_file_id = await archive_document(
        callback.bot,
        data["file_id"],
        caption
    )
    final_file_id = arch_file_id or data["file_id"]

    await add_file(
        lecture_id=data["lecture_id"],
        category=data["category"],
        file_name=data["custom_file_name"],
        telegram_file_id=final_file_id,
        uploader_id=user.id,
        uploader_name=user.full_name,
        specialization_id=data.get("spec_id"),
        description=data.get("description", ""),
        archive_message_id=arch_msg_id,
        file_type=data.get("file_type", "document"),
        file_size=data.get("file_size", 0)
    )

    await notify_new_content(
        bot=callback.bot,
        content_type=f"ملف إضافي ({cat_name}) 📁",
        title=data["custom_file_name"],
        uploader_name=user.full_name,
        day_name=data.get("day_name"),
        subject_name=data.get("subject_name"),
        lecture_name=data.get("lecture_name"),
        spec_name=data.get("spec_name"),
        category_name=cat_name
    )

    success_text = (
        "✅ <b>تم نشر الملف الإضافي بنجاح!</b>\n\n"
        f"📖 <b>المادة:</b> {data.get('subject_name')}\n"
        f"🎓 <b>المحاضرة:</b> {data.get('lecture_name')}\n"
        f"📂 <b>التصنيف:</b> {cat_name}\n"
        f"📄 <b>اسم الملف:</b> {data.get('custom_file_name')}\n\n"
        "يمكنك مواصلة رفع ملف آخر أيضاً أو العودة للقائمة الرئيسية 👇"
    )

    kb = get_consecutive_upload_keyboard(data["lecture_id"], data["category"])
    await callback.message.edit_text(success_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
