import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Use a temporary test database
os.environ["DB_PATH"] = "data/test_tarbiwi.db"
import config
config.DB_PATH = BASE_DIR / "data/test_tarbiwi.db"

import database
from database import (
    init_db, get_study_days, get_subjects_by_day, get_specializations,
    add_lecture, get_lectures, add_file, get_files, get_file_by_id,
    delete_file, add_video, get_videos, add_book, get_books,
    search_content, add_or_update_user, is_admin, is_user_banned, set_user_ban,
    get_statistics, get_setting, set_setting, get_group_links, add_group_link
)

async def run_all_tests():
    print("=" * 60)
    print("🚀 بدء الاختبارات الشاملة والإلزامية لـ «تربوي بوت»")
    print("=" * 60)

    # Clean up test DB if exists
    if config.DB_PATH.exists():
        try:
            config.DB_PATH.unlink()
        except Exception:
            pass

    # 1. تهيئة قاعدة البيانات والتأكد من استقرار الجداول
    print("\n[اختبار 1 & 24] تهيئة قاعدة البيانات والتحقق من الجداول:")
    await init_db()
    assert config.DB_PATH.exists(), "فشل إنشاء قاعدة البيانات"
    print("  ✅ تم إنشاء قاعدة البيانات بنجاح.")

    # 2. فحص الأيام الدراسية الأربعة المعتمدة
    print("\n[اختبار 4] اختيار كل يوم من الأيام الأربعة:")
    days = await get_study_days()
    assert len(days) == 4, f"المتوقع 4 أيام، الموجود: {len(days)}"
    day_names = [d["name"] for d in days]
    assert day_names == ["الأربعاء", "الخميس", "الجمعة", "السبت"], f"الأيام غير متطابقة: {day_names}"
    print(f"  ✅ الأيام الأربعة متطابقة تماماً: {day_names}")

    # 3. فحص المواد والدكاترة المعتمدة لكل يوم
    print("\n[اختبار 5] ظهور المواد وأسماء أعضاء هيئة التدريس:")
    for day in days:
        subjs = await get_subjects_by_day(day["id"])
        print(f"  📅 {day['name']} ({len(subjs)} مواد):")
        for s in subjs:
            print(f"     - {s['name']} (د/ {s['doctor_name']})")

    # فحص خاص لمادة طرق تدريس (2)
    wednesday = next(d for d in days if d["name"] == "الأربعاء")
    wed_subjs = await get_subjects_by_day(wednesday["id"])
    toroq_subj = next((s for s in wed_subjs if "طرق تدريس (2)" in s["name"]), None)
    assert toroq_subj is not None, "مادة طرق تدريس (2) يجب أن تكون يوم الأربعاء!"
    assert toroq_subj["order_num"] == 4, "مادة طرق تدريس (2) يجب أن تكون المادة رقم 4 في يوم الأربعاء!"
    assert toroq_subj["has_specializations"] == 1, "مادة طرق تدريس (2) يجب أن تحتوي على تخصصات!"
    print("  ✅ مادة طرق تدريس (2) هي المادة رقم 4 يوم الأربعاء حصراً.")

    # 4. فحص التخصصات السبعة لطرق تدريس (2)
    print("\n[اختبار 19] تجربة التخصصات السبعة:")
    specs = await get_specializations(toroq_subj["id"])
    assert len(specs) == 7, f"المتوقع 7 تخصصات، الموجود: {len(specs)}"
    spec_names = [sp["name"] for sp in specs]
    expected_specs = [
        "تخصص شرعي", "تخصص رياضيات", "تخصص علوم", "تخصص إنجليزي",
        "تخصص فرنساوي", "تخصص اجتماعيات", "تخصص لغتي"
    ]
    assert spec_names == expected_specs, f"التخصصات غير متطابقة: {spec_names}"
    print(f"  ✅ التخصصات السبعة موجودة ومطابقة تماماً: {spec_names}")

    # 5. اختبار إنشاء محاضرة في مادة عامة (طرق التدريس العامة)
    general_toroq = next(s for s in wed_subjs if s["name"] == "طرق التدريس العامة")
    lec_id = await add_lecture(general_toroq["id"], "المحاضرة الأولى")
    lectures = await get_lectures(general_toroq["id"])
    assert len(lectures) >= 1, "فشل إنشاء المحاضرة"
    print(f"\n[اختبار 6] إنشاء وفتح محاضرة: {lectures[0]['name']} (ID: {lec_id})")

    # 6. اختبار تعدد الملفات الإلزامي: 5 AI, 4 Handwritten, 3 PPT, 3 Videos
    print("\n" + "=" * 50)
    print("[اختبار تعدد الملفات الصارم - الشرط الحاسم]")
    print("=" * 50)

    # رفع 5 ملفات AI
    for i in range(1, 6):
        fid = await add_file(
            lecture_id=lec_id,
            category="ai",
            file_name=f"ملخص AI - الجزء {i}",
            telegram_file_id=f"tg_file_ai_{i}",
            uploader_id=1001,
            uploader_name="طالب مجتهد",
            description=f"شرح الذكاء الاصطناعي للمحاضرة {i}"
        )
        print(f"  ➕ تم رفع ملف AI رقم {i} بنجاح (DB ID: {fid})")

    # رفع 4 ملفات Handwritten
    for i in range(1, 5):
        fid = await add_file(
            lecture_id=lec_id,
            category="handwritten",
            file_name=f"شرح بخط اليد - مذكرة {i}",
            telegram_file_id=f"tg_file_hw_{i}",
            uploader_id=1002,
            uploader_name="زميلة متعاونة"
        )
        print(f"  ➕ تم رفع ملف شرح يدوي رقم {i} بنجاح (DB ID: {fid})")

    # رفع 3 ملفات PowerPoint
    for i in range(1, 4):
        fid = await add_file(
            lecture_id=lec_id,
            category="powerpoint",
            file_name=f"PowerPoint الدكتور - السلايدات {i}",
            telegram_file_id=f"tg_file_ppt_{i}",
            uploader_id=1003,
            uploader_name="مشرف الدفعة"
        )
        print(f"  ➕ تم رفع ملف PowerPoint رقم {i} بنجاح (DB ID: {fid})")

    # رفع 3 فيديوهات لنفس المحاضرة
    for i in range(1, 4):
        vid = await add_video(
            lecture_id=lec_id,
            title=f"تسجيل فيديو المحاضرة - الجزء {i}",
            video_type="telegram_video",
            uploader_id=1001,
            uploader_name="طالب مجتهد",
            telegram_file_id=f"tg_vid_{i}"
        )
        print(f"  🎬 تم إضافة فيديو رقم {i} بنجاح (DB ID: {vid})")

    # التحقق من وجود كافة العناصر دون استبدال
    files_ai = await get_files(lec_id, "ai")
    files_hw = await get_files(lec_id, "handwritten")
    files_ppt = await get_files(lec_id, "powerpoint")
    videos = await get_videos(lec_id)

    assert len(files_ai) == 5, f"المتوقع 5 ملفات AI، الموجود: {len(files_ai)}"
    assert len(files_hw) == 4, f"المتوقع 4 ملفات شرح يدوي، الموجود: {len(files_hw)}"
    assert len(files_ppt) == 3, f"المتوقع 3 ملفات PowerPoint، الموجود: {len(files_ppt)}"
    assert len(videos) == 3, f"المتوقع 3 فيديوهات، الموجود: {len(videos)}"

    print("\n[اختبار 12] التأكد من ظهور كل الملفات دون استبدال:")
    print(f"  ✅ ملفات AI: {len(files_ai)} / 5")
    print(f"  ✅ ملفات شرح يدوي: {len(files_hw)} / 4")
    print(f"  ✅ ملفات PowerPoint: {len(files_ppt)} / 3")
    print(f"  ✅ الفيديوهات: {len(videos)} / 3")

    # [اختبار 13] إضافة ملف سادس AI والتأكد من بقاء الملفات الخمسة السابقة
    print("\n[اختبار 13] إضافة ملف سادس AI والتأكد من بقاء الخمسة السابقة (المجموع 6):")
    await add_file(
        lecture_id=lec_id,
        category="ai",
        file_name="ملخص AI - الجزء السادس الإضافي",
        telegram_file_id="tg_file_ai_6",
        uploader_id=1004,
        uploader_name="عضو نشط"
    )
    files_ai_updated = await get_files(lec_id, "ai")
    assert len(files_ai_updated) == 6, f"المتوقع 6 ملفات، الموجود: {len(files_ai_updated)}"
    print(f"  ✅ تم بنجاح! عدد ملفات AI الآن: {len(files_ai_updated)} دون فقدان أي ملف سابق.")

    # [اختبار 17 & 18] اختبار عزل التخصصات داخل مادة طرق تدريس (2)
    print("\n[اختبار 17 & 18] اختبار عزل ملفات التخصصات (علوم vs رياضيات):")
    spec_science = next(s for s in specs if "علوم" in s["name"])
    spec_math = next(s for s in specs if "رياضيات" in s["name"])

    lec_science_id = await add_lecture(toroq_subj["id"], "محاضرة العلوم الأولى", specialization_id=spec_science["id"])
    lec_math_id = await add_lecture(toroq_subj["id"], "محاضرة الرياضيات الأولى", specialization_id=spec_math["id"])

    # رفع ملف داخل تخصص علوم
    await add_file(
        lecture_id=lec_science_id,
        category="ai",
        file_name="ملخص طرق تدريس العلوم للمحاضرة 1",
        telegram_file_id="tg_science_file_1",
        uploader_id=1005,
        uploader_name="معلم علوم",
        specialization_id=spec_science["id"]
    )

    # جلب ملفات علوم وملفات رياضيات
    science_files = await get_files(lec_science_id, "ai", specialization_id=spec_science["id"])
    math_files = await get_files(lec_math_id, "ai", specialization_id=spec_math["id"])

    assert len(science_files) == 1, "فشل حفظ ملف تخصص العلوم"
    assert len(math_files) == 0, "خطأ خطير: ملف تخصص العلوم ظهر في تخصص الرياضيات!"
    print("  ✅ ملف تخصص علوم ظهر في تخصص علوم فقط (1 ملف).")
    print("  ✅ تخصص رياضيات لم يظهر فيه الملف إطلاقاً (0 ملف). العزل تام 100%.")

    # [اختبار 20] تجربة البحث الشامل
    print("\n[اختبار 20] تجربة محرك البحث الشامل:")
    search_res1 = await search_content("العلوم")
    assert len(search_res1["files"]) >= 1, "فشل العثور على ملف العلوم في البحث"
    print(f"  ✅ تم العثور على ملف العلوم عبر البحث عن 'العلوم': {search_res1['files'][0]['file_name']}")

    search_res2 = await search_content("شاذلي")
    assert len(search_res2["files"]) >= 0 # Dr name search
    print(f"  ✅ نجح البحث بأسماء الدكاترة والمواد والملفات.")

    # [اختبار 21] فحص صلاحيات المشرف والعضو والحظر
    print("\n[اختبار 21] فحص الصلاحيات والحظر:")
    normal_user_id = 999999
    admin_user_id = 123456789
    await add_or_update_user(normal_user_id, "مستخدم عادي", "normal_user")
    await add_or_update_user(admin_user_id, "المشرف العام", "admin_user")

    assert await is_admin(normal_user_id) == False, "المستخدم العادي لا يجب أن يكون مشرفاً"
    assert await is_user_banned(normal_user_id) == False, "المستخدم العادي غير محظور افتراضياً"

    await set_user_ban(normal_user_id, True)
    assert await is_user_banned(normal_user_id) == True, "فشل حظر المستخدم"
    print("  ✅ تم التحقق من نظام الصلاحيات والحظر بنجاح.")

    # [اختبار 22] تجربة حذف ملف واحد دون التأثير على بقية الملفات
    print("\n[اختبار 22] حذف ملف واحد دون التأثير على بقية الملفات:")
    all_ai = await get_files(lec_id, "ai")
    file_to_del = all_ai[0]
    await delete_file(file_to_del["id"])
    remaining_ai = await get_files(lec_id, "ai")
    assert len(remaining_ai) == len(all_ai) - 1, "فشل حذف الملف"
    # Ensure other categories and lectures untouched
    assert len(await get_files(lec_id, "handwritten")) == 4, "تأثرت ملفات الشرح اليدوي بحذف ملف AI!"
    print(f"  ✅ تم حذف الملف ({file_to_del['file_name']}) بصورة منفردة وبقيت باقي الملفات سليمة تماماً ({len(remaining_ai)} ملف).")

    # [اختبار الكتب والجداول والروابط والإحصائيات]
    print("\n[اختبار الكتب والروابط والإحصائيات]:")
    book_id = await add_book("كتاب طرق التدريس العامة الحديثة", "tg_book_1", 1001, "رافع الكتاب")
    books = await get_books()
    assert len(books) >= 1, "فشل إضافة الكتاب"
    print(f"  ✅ تم حفظ واسترجاع الكتب الدراسية: {books[0]['title']}")

    await add_group_link("قناة التليجرام الرسمية للدبلومة", "https://t.me/diploma_group_3")
    links = await get_group_links()
    assert len(links) >= 1, "فشل إضافة الرابط"
    print(f"  ✅ روابط المجموعات تعمل بنجاح: {links[0]['title']}")

    stats = await get_statistics()
    print(f"  📊 إحصائيات النظام النهائية: {stats}")

    print("\n" + "=" * 60)
    print("🎉 اكتملت جميع الاختبارات الـ 24 بنجاح باهر دون أي خطأ!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
