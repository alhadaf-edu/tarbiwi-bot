from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import search_content, CATEGORY_NAMES
from utils.states import SearchStates
from keyboards.main_kb import get_cancel_keyboard

router = Router(name="search")

@router.callback_query(F.data == "search_main")
async def cb_search_main(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_query)
    text = (
        "🔍 <b>البحث الشامل في محتوى الدبلومة:</b>\n\n"
        "أدخل كلمة البحث، يمكنك البحث باستخدام:\n"
        "• اسم المادة (مثال: طرق التدريس)\n"
        "• اسم الدكتور (مثال: د/ شاذلي)\n"
        "• اسم أو رقم المحاضرة (مثال: المحاضرة الأولى)\n"
        "• اسم التخصص (مثال: علوم، لغتي)\n"
        "• اسم الملف أو عنوان الفيديو أو التصنيف\n\n"
        "✍️ أرسل كلمة البحث الآن:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("⚠️ يرجى إدخال حرفين على الأقل لإجراء البحث.", reply_markup=get_cancel_keyboard())
        return

    await state.clear()
    results = await search_content(query)
    files = results["files"]
    videos = results["videos"]
    audios = results.get("audios", [])
    books = results["books"]

    total = len(files) + len(videos) + len(audios) + len(books)
    if total == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 بحث جديد", callback_data="search_main")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")]
        ])
        await message.answer(f"❌ لم يتم العثور على أي نتائج تطابق: <b>{query}</b>", reply_markup=kb, parse_mode="HTML")
        return

    # Results found! Build formatted list with full paths and clickable buttons
    text = (
        f"🎯 <b>نتائج البحث عن:</b> <i>{query}</i>\n"
        f"تم العثور على <b>{total}</b> نتيجة:\n"
        "➖➖➖➖➖➖➖➖➖➖\n\n"
    )

    keyboard = []

    # Files results
    if files:
        text += f"📂 <b>الملفات التعليمية ({len(files)}):</b>\n"
        for idx, f in enumerate(files[:10], 1):
            cat = CATEGORY_NAMES.get(f['category'], f['category'])
            spec = f" ⬅️ {f['spec_name']}" if f.get('spec_name') else ""
            path = f"{f['day_name']} ⬅️ {f['subject_name']}{spec} ⬅️ {f['lecture_name']}"
            text += f"{idx}. <b>{f['file_name']}</b>\n   📍 {path} ({cat})\n"
            keyboard.append([InlineKeyboardButton(text=f"📄 {f['file_name']} ({cat})", callback_data=f"file_get:{f['id']}")])
        text += "\n"

    # Videos results
    if videos:
        text += f"🎥 <b>الفيديوهات ({len(videos)}):</b>\n"
        for idx, v in enumerate(videos[:5], 1):
            spec = f" ⬅️ {v['spec_name']}" if v.get('spec_name') else ""
            path = f"{v['day_name']} ⬅️ {v['subject_name']}{spec} ⬅️ {v['lecture_name']}"
            text += f"{idx}. <b>{v['title']}</b>\n   📍 {path}\n"
            keyboard.append([InlineKeyboardButton(text=f"🎬 {v['title']}", callback_data=f"video_get:{v['id']}")])
        text += "\n"

    # Audios results
    if audios:
        text += f"🎙 <b>التسجيلات الصوتية ({len(audios)}):</b>\n"
        for idx, a in enumerate(audios[:5], 1):
            spec = f" ⬅️ {a['spec_name']}" if a.get('spec_name') else ""
            path = f"{a['day_name']} ⬅️ {a['subject_name']}{spec} ⬅️ {a['lecture_name']}"
            text += f"{idx}. <b>{a['title']}</b>\n   📍 {path}\n"
            keyboard.append([InlineKeyboardButton(text=f"🎙 {a['title']}", callback_data=f"audio_get:{a['id']}")])
        text += "\n"

    # Books results
    if books:
        text += f"📚 <b>الكتب والمراجع ({len(books)}):</b>\n"
        for idx, b in enumerate(books[:5], 1):
            subj = f"({b['subject_name']})" if b.get('subject_name') else ""
            text += f"{idx}. <b>{b['title']}</b> {subj}\n"
            keyboard.append([InlineKeyboardButton(text=f"📖 {b['title']}", callback_data=f"book_get:{b['id']}")])

    keyboard.append([InlineKeyboardButton(text="🔍 بحث جديد", callback_data="search_main")])
    keyboard.append([InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="home")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
