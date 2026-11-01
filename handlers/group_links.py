from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_group_links

router = Router(name="group_links")

@router.callback_query(F.data == "group_links_main")
async def cb_group_links_main(callback: CallbackQuery):
    links = await get_group_links(include_hidden=False)

    text = (
        "🔗 <b>روابط المجموعات والقنوات المهمة:</b>\n\n"
        "إليك الروابط المعتمدة لمجموعات وقنوات دبلومة التأهيل التربوي – مجموعة 3:\n\n"
    )

    keyboard = []
    if not links:
        text += "<i>لم يتم نشر روابط حالياً.</i>"
    else:
        for lnk in links:
            keyboard.append([InlineKeyboardButton(text=f"🌐 {lnk['title']}", url=lnk['url'])])

    keyboard.append([InlineKeyboardButton(text="🏠 العودة للقائمة الرئيسية", callback_data="home")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()
