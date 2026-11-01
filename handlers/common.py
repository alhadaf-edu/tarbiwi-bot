from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from keyboards.main_kb import get_main_menu_keyboard
from database import is_admin, add_or_update_user

router = Router(name="common")

WELCOME_TEXT = (
    "✨ <b>أهلاً بك في «تربوي بوت» 🎓</b>\n\n"
    "المكتبة التعليمية التفاعلية الرسمية المخصصة لأعضاء:\n"
    "<b>دبلومة التأهيل التربوي أون لاين – مجموعة 3</b> 📚\n\n"
    "من خلال البوت يمكنك تصفح الكتب، الجداول، المحاضرات، الفيديوهات، والملخصات، "
    "أو مشاركة ورفع ملفات جديدة لمساعدة زملائك.\n\n"
    "اختر ما يناسبك من القائمة أدناه 👇"
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await add_or_update_user(user.id, user.full_name, user.username)
    admin_status = await is_admin(user.id)
    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(is_admin=admin_status),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "💡 <b>دليل استخدام تربوي بوت:</b>\n\n"
        "1️⃣ <b>عرض المنهج الدراسي:</b> استعراض الكتب أو اختيار اليوم الدراسي ومواده للوصول للمحاضرات والملفات والفيديوهات.\n"
        "2️⃣ <b>البحث عن ملف:</b> البحث الفوري عن أي مادة، دكتور، محاضرة، تخصص، ملف أو فيديو.\n"
        "3️⃣ <b>مشاركة ملف جديد:</b> رفع الكتب والملخصات وعروض البوربوينت والفيديوهات بسهولة.\n"
        "4️⃣ <b>روابط المجموعات:</b> الروابط الرسمية والقنوات المعتمدة للدبلومة.\n\n"
        "💬 لأي استفسار أو اقتراح، يمكنك التواصل مع مشرفي المجموعة."
    )
    await message.answer(text=text, parse_mode="HTML")

@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    admin_status = await is_admin(callback.from_user.id)
    try:
        await callback.message.edit_text(
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(is_admin=admin_status),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(is_admin=admin_status),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
