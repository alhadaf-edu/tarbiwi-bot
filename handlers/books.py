from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_books, get_book_by_id, get_schedules, get_schedule_by_id
from keyboards.study_kb import get_books_keyboard

router = Router(name="books")

@router.callback_query(F.data.startswith("books_list:"))
async def cb_books_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    books = await get_books()

    text = (
        "📖 <b>قسم تحميل الكتب والمراجع الدراسية:</b>\n\n"
        "هذا القسم مخصص للكتب المقررة والمراجع الإثرائية المعتمدة لدبلومة التأهيل التربوي.\n\n"
        f"📚 <b>إجمالي الكتب المتوفرة:</b> {len(books)}\n"
        "اضغط على أي كتاب لتحميله مباشرة 👇"
    )

    kb = get_books_keyboard(books, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("book_get:"))
async def cb_book_get(callback: CallbackQuery):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(book_id)
    if not book:
        await callback.answer("الكتاب غير موجود.", show_alert=True)
        return

    caption = (
        f"📖 <b>{book['title']}</b>\n\n"
        f"📌 <b>المادة المرتبطة:</b> {book.get('subject_name') or 'كتاب عام / غير محدد'}\n"
        f"👤 <b>رافع الكتاب:</b> {book.get('uploader_name') or 'عضو في الدبلومة'}\n"
        f"📅 <b>تاريخ الإضافة:</b> {str(book.get('created_at'))[:16]}\n"
    )
    if book.get("description"):
        caption += f"📝 <b>الوصف:</b> {book['description']}\n"

    try:
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=book["telegram_file_id"],
            caption=caption,
            parse_mode="HTML"
        )
        await callback.answer("✅ جاري إرسال الكتاب...")
    except Exception as e:
        await callback.answer(f"تعذر إرسال الكتاب: {e}", show_alert=True)

@router.callback_query(F.data.startswith("sched_get:"))
async def cb_sched_get(callback: CallbackQuery):
    sched_id = int(callback.data.split(":")[1])
    sched = await get_schedule_by_id(sched_id)
    if not sched:
        await callback.answer("الجدول غير موجود.", show_alert=True)
        return

    caption = (
        f"🗓 <b>{sched['title']}</b>\n\n"
        f"👤 <b>رافع الجدول:</b> {sched.get('uploader_name') or 'عضو في الدبلومة'}\n"
        f"📅 <b>تاريخ الإضافة:</b> {str(sched.get('created_at'))[:16]}\n"
    )
    if sched.get("description"):
        caption += f"📝 <b>الوصف:</b> {sched['description']}\n"

    try:
        if sched.get("file_type") == "photo":
            await callback.message.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=sched["telegram_file_id"],
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await callback.message.bot.send_document(
                chat_id=callback.from_user.id,
                document=sched["telegram_file_id"],
                caption=caption,
                parse_mode="HTML"
            )
        await callback.answer("✅ جاري إرسال الجدول...")
    except Exception as e:
        await callback.answer(f"تعذر إرسال الجدول: {e}", show_alert=True)
