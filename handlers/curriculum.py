from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_study_days, get_day_by_id, get_subjects_by_day, get_subject_by_id,
    get_specializations, get_specialization_by_id, get_lectures, get_lecture_by_id,
    get_files, get_file_by_id, get_videos, get_video_by_id, CATEGORY_NAMES
)
from keyboards.study_kb import (
    get_curriculum_menu, get_days_keyboard, get_subjects_keyboard,
    get_specializations_keyboard, get_lectures_keyboard, get_lecture_detail_keyboard,
    get_categories_keyboard, get_category_files_keyboard, get_videos_keyboard
)

router = Router(name="curriculum")

@router.callback_query(F.data == "curriculum_main")
async def cb_curriculum_main(callback: CallbackQuery):
    text = (
        "📚 <b>عرض المنهج الدراسي:</b>\n\n"
        "اختر القسم الذي ترغب في استعراضه:"
    )
    await callback.message.edit_text(text, reply_markup=get_curriculum_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "study_days_list")
async def cb_study_days_list(callback: CallbackQuery):
    days = await get_study_days()
    text = (
        "📅 <b>مواد الأيام الدراسية:</b>\n\n"
        "اختر اليوم الدراسي للاطلاع على مواده والمحاضرات المقررة:"
    )
    await callback.message.edit_text(text, reply_markup=get_days_keyboard(days), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("day_view:"))
async def cb_day_view(callback: CallbackQuery):
    day_id = int(callback.data.split(":")[1])
    day = await get_day_by_id(day_id)
    if not day:
        await callback.answer("اليوم غير موجود.", show_alert=True)
        return

    subjects = await get_subjects_by_day(day_id)
    text = (
        f"📅 <b>جدول يوم: {day['name']}</b>\n"
        f"اختر المادة لعرض محاضراتها وملفاتها:\n\n"
    )
    for idx, s in enumerate(subjects, 1):
        doc = f" ({s['doctor_name']})" if s.get('doctor_name') else ""
        text += f"{idx}. <b>{s['name']}</b>{doc}\n"

    await callback.message.edit_text(text, reply_markup=get_subjects_keyboard(day_id, day['name'], subjects), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("subj_view:"))
async def cb_subj_view(callback: CallbackQuery):
    subject_id = int(callback.data.split(":")[1])
    subject = await get_subject_by_id(subject_id)
    if not subject:
        await callback.answer("المادة غير موجودة.", show_alert=True)
        return

    # If the subject is طرق تدريس (2) or has specializations
    if subject.get("has_specializations"):
        specs = await get_specializations(subject_id)
        text = (
            f"📍 <b>المسار:</b> {subject['day_name']} ⬅️ <b>{subject['name']}</b>\n\n"
            f"👨‍🏫 <b>عضو هيئة التدريس:</b> {subject.get('doctor_name') or 'غير محدد'}\n\n"
            f"🎯 <b>اختر التخصص المطلوب:</b>"
        )
        await callback.message.edit_text(text, reply_markup=get_specializations_keyboard(subject_id, specs), parse_mode="HTML")
        await callback.answer()
        return

    # Regular subject without specializations
    lectures = await get_lectures(subject_id)
    text = (
        f"📍 <b>المسار:</b> {subject['day_name']} ⬅️ <b>{subject['name']}</b>\n"
        f"👨‍🏫 <b>عضو هيئة التدريس:</b> {subject.get('doctor_name') or 'غير محدد'}\n\n"
        f"🎓 <b>قائمة المحاضرات المتاحة:</b>\n"
    )
    if not lectures:
        text += "<i>لم تُضف أي محاضرات لهذه المادة بعد. يمكنك إضافة أول محاضرة الآن!</i>"

    back_cb = f"day_view:{subject['day_id']}"
    await callback.message.edit_text(text, reply_markup=get_lectures_keyboard(subject_id, lectures, back_callback=back_cb), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("spec_view:"))
async def cb_spec_view(callback: CallbackQuery):
    spec_id = int(callback.data.split(":")[1])
    spec = await get_specialization_by_id(spec_id)
    if not spec:
        await callback.answer("التخصص غير موجود.", show_alert=True)
        return

    subject = await get_subject_by_id(spec["subject_id"])
    lectures = await get_lectures(spec["subject_id"], specialization_id=spec_id)

    text = (
        f"📍 <b>المسار:</b> {subject['day_name']} ⬅️ {subject['name']} ⬅️ <b>{spec['name']}</b>\n\n"
        f"🎓 <b>محاضرات تخصص ({spec['name']}):</b>\n"
    )
    if not lectures:
        text += "<i>لا توجد محاضرات مضافة لهذا التخصص حتى الآن. يمكنك إضافة محاضرة جديدة الآن!</i>"

    back_cb = f"subj_view:{subject['id']}"
    await callback.message.edit_text(
        text,
        reply_markup=get_lectures_keyboard(subject['id'], lectures, spec_id=spec_id, back_callback=back_cb),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("lec_view:"))
async def cb_lec_view(callback: CallbackQuery):
    lecture_id = int(callback.data.split(":")[1])
    lecture = await get_lecture_by_id(lecture_id)
    if not lecture:
        await callback.answer("المحاضرة غير موجودة.", show_alert=True)
        return

    spec_part = f" ⬅️ {lecture['spec_name']}" if lecture.get("spec_name") else ""
    breadcrumb = f"{lecture['day_name']} ⬅️ {lecture['subject_name']}{spec_part} ⬅️ <b>{lecture['name']}</b>"

    text = (
        f"📍 <b>المسار:</b> {breadcrumb}\n\n"
        f"🎓 <b>{lecture['name']}</b>\n\n"
        f"اختر ما ترغب في عرضه لهذه المحاضرة:"
    )

    if lecture.get("specialization_id"):
        back_cb = f"spec_view:{lecture['specialization_id']}"
    else:
        back_cb = f"subj_view:{lecture['subject_id']}"

    await callback.message.edit_text(text, reply_markup=get_lecture_detail_keyboard(lecture_id, back_cb), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("lec_files_cats:"))
async def cb_lec_files_cats(callback: CallbackQuery):
    lecture_id = int(callback.data.split(":")[1])
    lecture = await get_lecture_by_id(lecture_id)
    if not lecture:
        await callback.answer("المحاضرة غير موجودة.", show_alert=True)
        return

    # Count files for each category
    spec_id = lecture.get("specialization_id")
    files_ai = await get_files(lecture_id, "ai", specialization_id=spec_id)
    files_hw = await get_files(lecture_id, "handwritten", specialization_id=spec_id)
    files_ppt = await get_files(lecture_id, "powerpoint", specialization_id=spec_id)

    counts = {
        "ai": len(files_ai),
        "handwritten": len(files_hw),
        "powerpoint": len(files_ppt)
    }

    spec_part = f" ⬅️ {lecture['spec_name']}" if lecture.get("spec_name") else ""
    breadcrumb = f"{lecture['day_name']} ⬅️ {lecture['subject_name']}{spec_part} ⬅️ {lecture['name']} ⬅️ <b>ملفات المحاضرة</b>"

    text = (
        f"📍 <b>المسار:</b> {breadcrumb}\n\n"
        f"اختر التصنيف لعرض جميع الملفات المرفوعة تحته:"
    )

    await callback.message.edit_text(text, reply_markup=get_categories_keyboard(lecture_id, counts), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("lec_cat_files:"))
async def cb_lec_cat_files(callback: CallbackQuery):
    parts = callback.data.split(":")
    lecture_id = int(parts[1])
    category = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    lecture = await get_lecture_by_id(lecture_id)
    if not lecture:
        await callback.answer("المحاضرة غير موجودة.", show_alert=True)
        return

    spec_id = lecture.get("specialization_id")
    files = await get_files(lecture_id, category, specialization_id=spec_id)

    cat_title = CATEGORY_NAMES.get(category, category)
    spec_part = f" ⬅️ {lecture['spec_name']}" if lecture.get("spec_name") else ""
    breadcrumb = f"{lecture['day_name']} ⬅️ {lecture['subject_name']}{spec_part} ⬅️ {lecture['name']} ⬅️ <b>{cat_title}</b>"

    text = (
        f"📍 <b>المسار:</b> {breadcrumb}\n"
        f"📁 <b>إجمالي الملفات المتاحة:</b> {len(files)} ملف\n\n"
    )

    if not files:
        text += "<i>لا توجد ملفات مرفوعة في هذا التصنيف حتى الآن. كن أول من يشارك ملفاً!</i>\n"
    else:
        text += "اضغط على أي ملف لاستعراض تفاصيله وتحميله مباشرة 👇\n"

    kb = get_category_files_keyboard(files, lecture_id, category, page=page)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("file_get:"))
async def cb_file_get(callback: CallbackQuery):
    file_id = int(callback.data.split(":")[1])
    file_data = await get_file_by_id(file_id)
    if not file_data:
        await callback.answer("الملف غير متوفر.", show_alert=True)
        return

    cat_title = CATEGORY_NAMES.get(file_data['category'], file_data['category'])
    spec_part = f" ⬅️ {file_data['spec_name']}" if file_data.get("spec_name") else ""
    breadcrumb = f"{file_data['day_name']} ⬅️ {file_data['subject_name']}{spec_part} ⬅️ {file_data['lecture_name']}"

    caption = (
        f"📄 <b>{file_data['file_name']}</b>\n\n"
        f"📍 <b>المسار:</b> {breadcrumb}\n"
        f"📂 <b>التصنيف:</b> {cat_title}\n"
        f"👤 <b>رافع الملف:</b> {file_data.get('uploader_name') or 'عضو في الدبلومة'}\n"
        f"📅 <b>تاريخ الإضافة:</b> {str(file_data.get('created_at'))[:16]}\n"
    )
    if file_data.get("description"):
        caption += f"📝 <b>الوصف:</b> {file_data['description']}\n"

    # Send document to user
    try:
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=file_data["telegram_file_id"],
            caption=caption,
            parse_mode="HTML"
        )
        await callback.answer("✅ تم إرسال الملف بنجاح.")
    except Exception as e:
        await callback.answer(f"تعذر إرسال الملف: {e}", show_alert=True)

@router.callback_query(F.data.startswith("lec_videos:"))
async def cb_lec_videos(callback: CallbackQuery):
    parts = callback.data.split(":")
    lecture_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0

    lecture = await get_lecture_by_id(lecture_id)
    if not lecture:
        await callback.answer("المحاضرة غير موجودة.", show_alert=True)
        return

    spec_id = lecture.get("specialization_id")
    videos = await get_videos(lecture_id, specialization_id=spec_id)

    spec_part = f" ⬅️ {lecture['spec_name']}" if lecture.get("spec_name") else ""
    breadcrumb = f"{lecture['day_name']} ⬅️ {lecture['subject_name']}{spec_part} ⬅️ {lecture['name']} ⬅️ <b>فيديوهات المحاضرة</b>"

    text = (
        f"📍 <b>المسار:</b> {breadcrumb}\n"
        f"🎥 <b>إجمالي الفيديوهات المتاحة:</b> {len(videos)}\n\n"
    )
    if not videos:
        text += "<i>لا توجد فيديوهات مضافة لهذه المحاضرة حتى الآن. يمكنك إضافة فيديو الآن!</i>\n"
    else:
        text += "اختر الفيديو لمشاهدته أو فتح الرابط مباشرة 👇\n"

    kb = get_videos_keyboard(videos, lecture_id, page=page)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("video_get:"))
async def cb_video_get(callback: CallbackQuery):
    video_id = int(callback.data.split(":")[1])
    v = await get_video_by_id(video_id)
    if not v:
        await callback.answer("الفيديو غير متوفر.", show_alert=True)
        return

    spec_part = f" ⬅️ {v['spec_name']}" if v.get("spec_name") else ""
    breadcrumb = f"{v['day_name']} ⬅️ {v['subject_name']}{spec_part} ⬅️ {v['lecture_name']}"

    text = (
        f"🎬 <b>{v['title']}</b>\n\n"
        f"📍 <b>المسار:</b> {breadcrumb}\n"
        f"👤 <b>بواسطة:</b> {v.get('uploader_name') or 'عضو في الدبلومة'}\n"
        f"📅 <b>تاريخ الإضافة:</b> {str(v.get('created_at'))[:16]}\n"
    )
    if v.get("description"):
        text += f"📝 <b>الوصف:</b> {v['description']}\n"

    if v["video_type"] == "telegram_video" and v.get("telegram_file_id"):
        try:
            await callback.message.bot.send_video(
                chat_id=callback.from_user.id,
                video=v["telegram_file_id"],
                caption=text,
                parse_mode="HTML"
            )
            await callback.answer("✅ تم إرسال الفيديو.")
        except Exception as e:
            await callback.answer(f"تعذر إرسال الفيديو: {e}", show_alert=True)
    else:
        # External URL
        url = v.get("external_url", "")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 فتح رابط الفيديو الخارجي", url=url)],
            [InlineKeyboardButton(text="🔙 رجوع للفيديوهات", callback_data=f"lec_videos:{v['lecture_id']}:0")]
        ])
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
