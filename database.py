import aiosqlite
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from config import DB_PATH, ADMIN_IDS

CATEGORY_NAMES = {
    "ai": "ملخص AI",
    "handwritten": "شرح بخط اليد",
    "powerpoint": "PowerPoint الدكتور"
}

CATEGORY_ICONS = {
    "ai": "🤖",
    "handwritten": "✍️",
    "powerpoint": "📊"
}

@asynccontextmanager
async def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db

async def init_db():
    """Initializes tables and seeds base curriculum data safely without overwriting."""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS study_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                order_num INTEGER NOT NULL
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                doctor_name TEXT,
                order_num INTEGER NOT NULL,
                has_specializations INTEGER DEFAULT 0,
                FOREIGN KEY (day_id) REFERENCES study_days(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS specializations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS lectures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                specialization_id INTEGER NULL,
                name TEXT NOT NULL,
                order_num INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE CASCADE
            );
        """)

        # CRITICAL: files table has NO UNIQUE constraint on (lecture_id, category)
        # to allow UNLIMITED files per category per lecture!
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_id INTEGER NOT NULL,
                specialization_id INTEGER NULL,
                category TEXT NOT NULL,
                file_name TEXT NOT NULL,
                description TEXT,
                telegram_file_id TEXT NOT NULL,
                archive_message_id INTEGER NULL,
                uploader_id INTEGER NOT NULL,
                uploader_name TEXT,
                file_type TEXT DEFAULT 'document',
                file_size INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE,
                FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_id INTEGER NOT NULL,
                specialization_id INTEGER NULL,
                title TEXT NOT NULL,
                description TEXT,
                video_type TEXT NOT NULL,
                telegram_file_id TEXT NULL,
                external_url TEXT NULL,
                archive_message_id INTEGER NULL,
                uploader_id INTEGER NOT NULL,
                uploader_name TEXT,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE,
                FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS audios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_id INTEGER NOT NULL,
                specialization_id INTEGER NULL,
                title TEXT NOT NULL,
                description TEXT,
                telegram_file_id TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                archive_message_id INTEGER NULL,
                uploader_id INTEGER NOT NULL,
                uploader_name TEXT,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE,
                FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NULL,
                title TEXT NOT NULL,
                description TEXT,
                telegram_file_id TEXT NOT NULL,
                archive_message_id INTEGER NULL,
                uploader_id INTEGER NOT NULL,
                uploader_name TEXT,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                telegram_file_id TEXT NOT NULL,
                archive_message_id INTEGER NULL,
                uploader_id INTEGER NOT NULL,
                uploader_name TEXT,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                order_num INTEGER DEFAULT 1,
                is_visible INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subject_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                doctor_name TEXT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (day_id) REFERENCES study_days(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        await db.commit()

        # Seed Days if empty
        cursor = await db.execute("SELECT COUNT(*) FROM study_days;")
        count = (await cursor.fetchone())[0]
        if count == 0:
            days_data = [
                ("الأربعاء", 1),
                ("الخميس", 2),
                ("الجمعة", 3),
                ("السبت", 4),
            ]
            await db.executemany("INSERT INTO study_days (name, order_num) VALUES (?, ?);", days_data)
            await db.commit()

        # Seed Subjects if empty
        cursor = await db.execute("SELECT COUNT(*) FROM subjects;")
        count_subj = (await cursor.fetchone())[0]
        if count_subj == 0:
            # Fetch day IDs
            cursor = await db.execute("SELECT id, name FROM study_days;")
            day_rows = await cursor.fetchall()
            day_map = {row["name"]: row["id"] for row in day_rows}

            subjects_data = [
                # يوم الأربعاء
                (day_map["الأربعاء"], "طرق التدريس العامة", "أ.د/ محمد عبد الوهاب محمد", 1, 0),
                (day_map["الأربعاء"], "الإدارة والتخطيط", "د/ شاذلي يونس علي", 2, 0),
                (day_map["الأربعاء"], "التدريس المصغر", "أ.د/ خلف الديب عثمان محمد", 3, 0),
                (day_map["الأربعاء"], "طرق تدريس (2)", "جميع التخصصات", 4, 1), # مادة طرق تدريس (2) حصراً يوم الأربعاء
                (day_map["الأربعاء"], "الصحة النفسية وعلم النفس الاجتماعي", "أ.د/ نجلاء محمود رسلان", 5, 0),

                # يوم الخميس
                (day_map["الخميس"], "التربية الإسلامية", "أ.د/ محمود يوسف محمد", 1, 0),
                (day_map["الخميس"], "الفكر التربوي الإسلامي", "أ.د/ محمود يوسف محمد", 2, 0),
                (day_map["الخميس"], "التربية ومشكلات المجتمع", "أ.د/ محمد شكري وزير", 3, 0),
                (day_map["الخميس"], "علم النفس التعليمي (1)", "أ.د/ منال علي الخولي", 4, 0),

                # يوم الجمعة
                (day_map["الجمعة"], "التربية المقارنة", "د/ محمد سعد زكي", 1, 0),
                (day_map["الجمعة"], "الوسائل التعليمية", "د/ بسيوني عبد الرحمن العطار", 2, 0),
                (day_map["الجمعة"], "علم نفس النمو", "أ.م.د/ حمدي حامد سالم", 3, 0),

                # يوم السبت
                (day_map["السبت"], "المناهج", "أ.د/ عصام محمد أبو الخير", 1, 0),
                (day_map["السبت"], "الأصول الاجتماعية والثقافية للتربية", "أ.د/ جمال رجب عبد الحسيب", 2, 0),
                (day_map["السبت"], "الأصول الفلسفية للتربية", "د/ محمود أحمد حموده", 3, 0),
                (day_map["السبت"], "تاريخ التربية ونظام التعليم", "أ.د/ التهامي محمد إبراهيم", 4, 0),
                (day_map["السبت"], "علم النفس التعليمي (2)", "أ.د/ أيمن منير الخصوصي", 5, 0),
            ]
            await db.executemany("""
                INSERT INTO subjects (day_id, name, doctor_name, order_num, has_specializations)
                VALUES (?, ?, ?, ?, ?);
            """, subjects_data)
            await db.commit()

        # Seed Specializations for طرق تدريس (2) if empty
        cursor = await db.execute("SELECT id FROM subjects WHERE has_specializations = 1 LIMIT 1;")
        toroq_subj = await cursor.fetchone()
        if toroq_subj:
            toroq_id = toroq_subj["id"]
            cursor = await db.execute("SELECT COUNT(*) FROM specializations WHERE subject_id = ?;", (toroq_id,))
            count_spec = (await cursor.fetchone())[0]
            if count_spec == 0:
                specs_data = [
                    (toroq_id, "تخصص شرعي", 1),
                    (toroq_id, "تخصص رياضيات", 2),
                    (toroq_id, "تخصص علوم", 3),
                    (toroq_id, "تخصص إنجليزي", 4),
                    (toroq_id, "تخصص فرنساوي", 5),
                    (toroq_id, "تخصص اجتماعيات", 6),
                    (toroq_id, "تخصص لغتي", 7),
                ]
                await db.executemany("""
                    INSERT INTO specializations (subject_id, name, order_num)
                    VALUES (?, ?, ?);
                """, specs_data)
                await db.commit()

        # Seed default settings if not exists
        default_settings = [
            ("notifications_enabled", "1"),
            ("membership_check_enabled", "0"),
            ("archive_channel_id", ""),
            ("main_group_id", "")
        ]
        for key, val in default_settings:
            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?);", (key, val))
        
        # Seed default initial link if empty
        cursor = await db.execute("SELECT COUNT(*) FROM group_links;")
        if (await cursor.fetchone())[0] == 0:
            await db.execute("""
                INSERT INTO group_links (title, url, order_num, is_visible)
                VALUES (?, ?, ?, 1);
            """, ("قناة الإعلانات الرسمية للدبلومة", "https://t.me/telegram", 1))

        await db.commit()

# --- Users ---
async def add_or_update_user(user_id: int, full_name: str, username: Optional[str]) -> None:
    is_admin = 1 if user_id in ADMIN_IDS else 0
    async with get_db() as db:
        await db.execute("""
            INSERT INTO users (user_id, full_name, username, is_admin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                is_admin = CASE WHEN users.is_admin = 1 THEN 1 ELSE excluded.is_admin END;
        """, (user_id, full_name, username, is_admin))
        await db.commit()

async def is_user_banned(user_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("SELECT is_banned FROM users WHERE user_id = ?;", (user_id,))
        row = await cursor.fetchone()
        return bool(row["is_banned"]) if row else False

async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    async with get_db() as db:
        cursor = await db.execute("SELECT is_admin FROM users WHERE user_id = ?;", (user_id,))
        row = await cursor.fetchone()
        return bool(row["is_admin"]) if row else False

async def set_user_ban(user_id: int, is_banned: bool) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?;", (1 if is_banned else 0, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def set_user_admin(user_id: int, is_admin_val: bool) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?;", (1 if is_admin_val else 0, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_all_users() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users ORDER BY joined_at DESC;")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# --- Study Days & Subjects & Specializations ---
async def get_study_days() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM study_days ORDER BY order_num ASC;")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_day_by_id(day_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM study_days WHERE id = ?;", (day_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_study_day(name: str) -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(order_num) as m FROM study_days;")
        row = await cursor.fetchone()
        order_num = (row["m"] or 0) + 1
        cursor = await db.execute("INSERT INTO study_days (name, order_num) VALUES (?, ?);", (name, order_num))
        await db.commit()
        return cursor.lastrowid

async def update_study_day(day_id: int, name: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE study_days SET name = ? WHERE id = ?;", (name, day_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_study_day(day_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM study_days WHERE id = ?;", (day_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_subjects_by_day(day_id: int) -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM subjects WHERE day_id = ? ORDER BY order_num ASC;", (day_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_subject_by_id(subject_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT s.*, d.name as day_name
            FROM subjects s
            JOIN study_days d ON s.day_id = d.id
            WHERE s.id = ?;
        """, (subject_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_subject(day_id: int, name: str, doctor_name: Optional[str] = "", has_specializations: int = 0) -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(order_num) as m FROM subjects WHERE day_id = ?;", (day_id,))
        row = await cursor.fetchone()
        order_num = (row["m"] or 0) + 1
        cursor = await db.execute("""
            INSERT INTO subjects (day_id, name, doctor_name, order_num, has_specializations)
            VALUES (?, ?, ?, ?, ?);
        """, (day_id, name, doctor_name, order_num, has_specializations))
        await db.commit()
        return cursor.lastrowid

async def update_subject(subject_id: int, name: str, doctor_name: Optional[str]) -> bool:
    async with get_db() as db:
        cursor = await db.execute("""
            UPDATE subjects SET name = ?, doctor_name = ? WHERE id = ?;
        """, (name, doctor_name, subject_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_subject(subject_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM subjects WHERE id = ?;", (subject_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_specializations(subject_id: int) -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM specializations WHERE subject_id = ? ORDER BY order_num ASC;", (subject_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_specialization_by_id(spec_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM specializations WHERE id = ?;", (spec_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_specialization(subject_id: int, name: str) -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(order_num) as m FROM specializations WHERE subject_id = ?;", (subject_id,))
        row = await cursor.fetchone()
        order_num = (row["m"] or 0) + 1
        cursor = await db.execute("""
            INSERT INTO specializations (subject_id, name, order_num)
            VALUES (?, ?, ?);
        """, (subject_id, name, order_num))
        await db.commit()
        return cursor.lastrowid

async def update_specialization(spec_id: int, name: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE specializations SET name = ? WHERE id = ?;", (name, spec_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_specialization(spec_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM specializations WHERE id = ?;", (spec_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Lectures ---
async def get_lectures(subject_id: int, specialization_id: Optional[int] = None) -> List[Dict[str, Any]]:
    async with get_db() as db:
        if specialization_id is not None:
            cursor = await db.execute("""
                SELECT * FROM lectures 
                WHERE subject_id = ? AND specialization_id = ? AND is_active = 1
                ORDER BY order_num ASC, id ASC;
            """, (subject_id, specialization_id))
        else:
            cursor = await db.execute("""
                SELECT * FROM lectures 
                WHERE subject_id = ? AND specialization_id IS NULL AND is_active = 1
                ORDER BY order_num ASC, id ASC;
            """, (subject_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_lecture_by_id(lecture_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT l.*, s.name as subject_name, d.name as day_name, sp.name as spec_name
            FROM lectures l
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON l.specialization_id = sp.id
            WHERE l.id = ?;
        """, (lecture_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_lecture(subject_id: int, name: str, specialization_id: Optional[int] = None) -> int:
    async with get_db() as db:
        if specialization_id is not None:
            cursor = await db.execute("SELECT MAX(order_num) as m FROM lectures WHERE subject_id = ? AND specialization_id = ?;", (subject_id, specialization_id))
        else:
            cursor = await db.execute("SELECT MAX(order_num) as m FROM lectures WHERE subject_id = ? AND specialization_id IS NULL;", (subject_id,))
        row = await cursor.fetchone()
        order_num = (row["m"] or 0) + 1
        cursor = await db.execute("""
            INSERT INTO lectures (subject_id, specialization_id, name, order_num)
            VALUES (?, ?, ?, ?);
        """, (subject_id, specialization_id, name, order_num))
        await db.commit()
        return cursor.lastrowid

async def update_lecture(lecture_id: int, name: str, order_num: Optional[int] = None) -> bool:
    async with get_db() as db:
        if order_num is not None:
            cursor = await db.execute("UPDATE lectures SET name = ?, order_num = ? WHERE id = ?;", (name, order_num, lecture_id))
        else:
            cursor = await db.execute("UPDATE lectures SET name = ? WHERE id = ?;", (name, lecture_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_lecture(lecture_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM lectures WHERE id = ?;", (lecture_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Files (Unlimited Multiple Files per Category) ---
async def add_file(
    lecture_id: int,
    category: str,
    file_name: str,
    telegram_file_id: str,
    uploader_id: int,
    uploader_name: str,
    specialization_id: Optional[int] = None,
    description: Optional[str] = "",
    archive_message_id: Optional[int] = None,
    file_type: str = "document",
    file_size: int = 0
) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO files (
                lecture_id, specialization_id, category, file_name, description,
                telegram_file_id, archive_message_id, uploader_id, uploader_name,
                file_type, file_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            lecture_id, specialization_id, category, file_name, description,
            telegram_file_id, archive_message_id, uploader_id, uploader_name,
            file_type, file_size
        ))
        await db.commit()
        return cursor.lastrowid

async def get_files(
    lecture_id: int,
    category: str,
    specialization_id: Optional[int] = None,
    include_hidden: bool = False,
    order_by: str = "created_at DESC"
) -> List[Dict[str, Any]]:
    async with get_db() as db:
        hidden_clause = "" if include_hidden else "AND is_hidden = 0"
        
        # Validating order_by safely
        valid_orders = {
            "created_at DESC": "created_at DESC",
            "created_at ASC": "created_at ASC",
            "file_name ASC": "file_name ASC",
            "file_name DESC": "file_name DESC"
        }
        safe_order = valid_orders.get(order_by, "created_at DESC")

        if specialization_id is not None:
            query = f"""
                SELECT * FROM files
                WHERE lecture_id = ? AND category = ? AND specialization_id = ? {hidden_clause}
                ORDER BY {safe_order};
            """
            cursor = await db.execute(query, (lecture_id, category, specialization_id))
        else:
            query = f"""
                SELECT * FROM files
                WHERE lecture_id = ? AND category = ? {hidden_clause}
                ORDER BY {safe_order};
            """
            cursor = await db.execute(query, (lecture_id, category))

        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_file_by_id(file_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT f.*, l.name as lecture_name, s.name as subject_name, d.name as day_name, sp.name as spec_name
            FROM files f
            JOIN lectures l ON f.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON f.specialization_id = sp.id
            WHERE f.id = ?;
        """, (file_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_file(file_id: int, file_name: Optional[str] = None, description: Optional[str] = None, category: Optional[str] = None, lecture_id: Optional[int] = None) -> bool:
    async with get_db() as db:
        updates = []
        params = []
        if file_name is not None:
            updates.append("file_name = ?")
            params.append(file_name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if lecture_id is not None:
            updates.append("lecture_id = ?")
            params.append(lecture_id)
        if not updates:
            return False
        params.append(file_id)
        cursor = await db.execute(f"UPDATE files SET {', '.join(updates)} WHERE id = ?;", params)
        await db.commit()
        return cursor.rowcount > 0

async def delete_file(file_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM files WHERE id = ?;", (file_id,))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_file_hidden(file_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE files SET is_hidden = CASE WHEN is_hidden = 1 THEN 0 ELSE 1 END WHERE id = ?;", (file_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Videos (Multiple Videos per Lecture) ---
async def add_video(
    lecture_id: int,
    title: str,
    video_type: str,
    uploader_id: int,
    uploader_name: str,
    specialization_id: Optional[int] = None,
    description: Optional[str] = "",
    telegram_file_id: Optional[str] = None,
    external_url: Optional[str] = None,
    archive_message_id: Optional[int] = None
) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO videos (
                lecture_id, specialization_id, title, description, video_type,
                telegram_file_id, external_url, archive_message_id, uploader_id, uploader_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            lecture_id, specialization_id, title, description, video_type,
            telegram_file_id, external_url, archive_message_id, uploader_id, uploader_name
        ))
        await db.commit()
        return cursor.lastrowid

async def get_videos(
    lecture_id: int,
    specialization_id: Optional[int] = None,
    include_hidden: bool = False
) -> List[Dict[str, Any]]:
    async with get_db() as db:
        hidden_clause = "" if include_hidden else "AND is_hidden = 0"
        if specialization_id is not None:
            cursor = await db.execute(f"""
                SELECT * FROM videos
                WHERE lecture_id = ? AND specialization_id = ? {hidden_clause}
                ORDER BY created_at DESC;
            """, (lecture_id, specialization_id))
        else:
            cursor = await db.execute(f"""
                SELECT * FROM videos
                WHERE lecture_id = ? {hidden_clause}
                ORDER BY created_at DESC;
            """, (lecture_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_video_by_id(video_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT v.*, l.name as lecture_name, s.name as subject_name, d.name as day_name, sp.name as spec_name
            FROM videos v
            JOIN lectures l ON v.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON v.specialization_id = sp.id
            WHERE v.id = ?;
        """, (video_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_video(video_id: int, title: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE videos SET title = ? WHERE id = ?;", (title, video_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_video(video_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM videos WHERE id = ?;", (video_id,))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_video_hidden(video_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE videos SET is_hidden = CASE WHEN is_hidden = 1 THEN 0 ELSE 1 END WHERE id = ?;", (video_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Audios ---
async def add_audio(
    lecture_id: int,
    title: str,
    telegram_file_id: str,
    uploader_id: int,
    uploader_name: str,
    specialization_id: Optional[int] = None,
    description: Optional[str] = "",
    duration: int = 0,
    file_size: int = 0,
    archive_message_id: Optional[int] = None,
    audio_type: Optional[str] = "audio",
    **kwargs
) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO audios (
                lecture_id, specialization_id, title, description, telegram_file_id,
                duration, file_size, archive_message_id, uploader_id, uploader_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            lecture_id, specialization_id, title, description, telegram_file_id,
            duration, file_size, archive_message_id, uploader_id, uploader_name
        ))
        await db.commit()
        return cursor.lastrowid

async def get_audios(
    lecture_id: int,
    specialization_id: Optional[int] = None,
    include_hidden: bool = False
) -> List[Dict[str, Any]]:
    async with get_db() as db:
        hidden_clause = "" if include_hidden else "AND is_hidden = 0"
        if specialization_id is not None:
            cursor = await db.execute(f"""
                SELECT * FROM audios
                WHERE lecture_id = ? AND specialization_id = ? {hidden_clause}
                ORDER BY created_at DESC;
            """, (lecture_id, specialization_id))
        else:
            cursor = await db.execute(f"""
                SELECT * FROM audios
                WHERE lecture_id = ? {hidden_clause}
                ORDER BY created_at DESC;
            """, (lecture_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_audio_by_id(audio_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT a.*, l.name as lecture_name, s.name as subject_name, d.name as day_name, sp.name as spec_name
            FROM audios a
            JOIN lectures l ON a.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON a.specialization_id = sp.id
            WHERE a.id = ?;
        """, (audio_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_audio(audio_id: int, title: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE audios SET title = ? WHERE id = ?;", (title, audio_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_audio(audio_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM audios WHERE id = ?;", (audio_id,))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_audio_hidden(audio_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE audios SET is_hidden = CASE WHEN is_hidden = 1 THEN 0 ELSE 1 END WHERE id = ?;", (audio_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Books ---
async def add_book(
    title: str,
    telegram_file_id: str,
    uploader_id: int,
    uploader_name: str,
    subject_id: Optional[int] = None,
    description: Optional[str] = "",
    archive_message_id: Optional[int] = None
) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO books (subject_id, title, description, telegram_file_id, archive_message_id, uploader_id, uploader_name)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (subject_id, title, description, telegram_file_id, archive_message_id, uploader_id, uploader_name))
        await db.commit()
        return cursor.lastrowid

async def get_books(subject_id: Optional[int] = None, search_query: Optional[str] = None, include_hidden: bool = False) -> List[Dict[str, Any]]:
    async with get_db() as db:
        query = """
            SELECT b.*, s.name as subject_name
            FROM books b
            LEFT JOIN subjects s ON b.subject_id = s.id
            WHERE 1=1
        """
        params = []
        if not include_hidden:
            query += " AND b.is_hidden = 0"
        if subject_id is not None:
            query += " AND b.subject_id = ?"
            params.append(subject_id)
        if search_query:
            query += " AND (b.title LIKE ? OR b.description LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        query += " ORDER BY b.created_at DESC;"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT b.*, s.name as subject_name
            FROM books b
            LEFT JOIN subjects s ON b.subject_id = s.id
            WHERE b.id = ?;
        """, (book_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_book(book_id: int, title: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE books SET title = ? WHERE id = ?;", (title, book_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_book(book_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM books WHERE id = ?;", (book_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Schedules ---
async def add_schedule(
    title: str,
    telegram_file_id: str,
    uploader_id: int,
    uploader_name: str,
    description: Optional[str] = "",
    archive_message_id: Optional[int] = None
) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO schedules (title, description, telegram_file_id, archive_message_id, uploader_id, uploader_name)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (title, description, telegram_file_id, archive_message_id, uploader_id, uploader_name))
        await db.commit()
        return cursor.lastrowid

async def get_schedules(include_hidden: bool = False) -> List[Dict[str, Any]]:
    async with get_db() as db:
        hidden_clause = "" if include_hidden else "WHERE is_hidden = 0"
        cursor = await db.execute(f"SELECT * FROM schedules {hidden_clause} ORDER BY created_at DESC;")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_schedule_by_id(sched_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM schedules WHERE id = ?;", (sched_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def delete_schedule(sched_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM schedules WHERE id = ?;", (sched_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Group Links ---
async def get_group_links(include_hidden: bool = False) -> List[Dict[str, Any]]:
    async with get_db() as db:
        hidden_clause = "" if include_hidden else "WHERE is_visible = 1"
        cursor = await db.execute(f"SELECT * FROM group_links {hidden_clause} ORDER BY order_num ASC, id ASC;")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def add_group_link(title: str, url: str) -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(order_num) as m FROM group_links;")
        m = (await cursor.fetchone())["m"] or 0
        cursor = await db.execute("""
            INSERT INTO group_links (title, url, order_num, is_visible)
            VALUES (?, ?, ?, 1);
        """, (title, url, m + 1))
        await db.commit()
        return cursor.lastrowid

async def update_group_link(link_id: int, title: str, url: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE group_links SET title = ?, url = ? WHERE id = ?;", (title, url, link_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_group_link(link_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM group_links WHERE id = ?;", (link_id,))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_group_link_visibility(link_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE group_links SET is_visible = CASE WHEN is_visible = 1 THEN 0 ELSE 1 END WHERE id = ?;", (link_id,))
        await db.commit()
        return cursor.rowcount > 0

# --- Subject Suggestions ---
async def add_subject_suggestion(day_id: int, name: str, doctor_name: Optional[str], user_id: int, user_name: str) -> int:
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO subject_suggestions (day_id, name, doctor_name, user_id, user_name)
            VALUES (?, ?, ?, ?, ?);
        """, (day_id, name, doctor_name, user_id, user_name))
        await db.commit()
        return cursor.lastrowid

async def get_pending_suggestions() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT s.*, d.name as day_name
            FROM subject_suggestions s
            JOIN study_days d ON s.day_id = d.id
            WHERE s.status = 'pending'
            ORDER BY s.created_at ASC;
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def review_suggestion(suggestion_id: int, status: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("UPDATE subject_suggestions SET status = ? WHERE id = ?;", (status, suggestion_id))
        await db.commit()
        return cursor.rowcount > 0

# --- Comprehensive Global Search ---
async def search_content(query: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Searches across:
    - Files (by file_name, description, category, subject, doctor, lecture, specialization)
    - Videos (by title, description, subject, doctor, lecture, specialization)
    - Books (by title, description, subject)
    Returns full path context for every matched result!
    """
    query_term = f"%{query.strip()}%"
    results = {
        "files": [],
        "videos": [],
        "audios": [],
        "books": []
    }
    async with get_db() as db:
        # Search Files
        cursor = await db.execute("""
            SELECT f.*, l.name as lecture_name, s.name as subject_name, d.name as day_name,
                   s.doctor_name, sp.name as spec_name
            FROM files f
            JOIN lectures l ON f.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON f.specialization_id = sp.id
            WHERE f.is_hidden = 0 AND (
                f.file_name LIKE ? OR
                f.description LIKE ? OR
                f.category LIKE ? OR
                s.name LIKE ? OR
                s.doctor_name LIKE ? OR
                l.name LIKE ? OR
                sp.name LIKE ?
            )
            ORDER BY f.created_at DESC LIMIT 25;
        """, (query_term, query_term, query_term, query_term, query_term, query_term, query_term))
        results["files"] = [dict(r) for r in await cursor.fetchall()]

        # Search Videos
        cursor = await db.execute("""
            SELECT v.*, l.name as lecture_name, s.name as subject_name, d.name as day_name,
                   s.doctor_name, sp.name as spec_name
            FROM videos v
            JOIN lectures l ON v.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON v.specialization_id = sp.id
            WHERE v.is_hidden = 0 AND (
                v.title LIKE ? OR
                v.description LIKE ? OR
                s.name LIKE ? OR
                s.doctor_name LIKE ? OR
                l.name LIKE ? OR
                sp.name LIKE ?
            )
            ORDER BY v.created_at DESC LIMIT 25;
        """, (query_term, query_term, query_term, query_term, query_term, query_term))
        results["videos"] = [dict(r) for r in await cursor.fetchall()]

        # Search Audios
        cursor = await db.execute("""
            SELECT a.*, l.name as lecture_name, s.name as subject_name, d.name as day_name,
                   s.doctor_name, sp.name as spec_name
            FROM audios a
            JOIN lectures l ON a.lecture_id = l.id
            JOIN subjects s ON l.subject_id = s.id
            JOIN study_days d ON s.day_id = d.id
            LEFT JOIN specializations sp ON a.specialization_id = sp.id
            WHERE a.is_hidden = 0 AND (
                a.title LIKE ? OR
                a.description LIKE ? OR
                s.name LIKE ? OR
                s.doctor_name LIKE ? OR
                l.name LIKE ? OR
                sp.name LIKE ?
            )
            ORDER BY a.created_at DESC LIMIT 25;
        """, (query_term, query_term, query_term, query_term, query_term, query_term))
        results["audios"] = [dict(r) for r in await cursor.fetchall()]

        # Search Books
        cursor = await db.execute("""
            SELECT b.*, s.name as subject_name
            FROM books b
            LEFT JOIN subjects s ON b.subject_id = s.id
            WHERE b.is_hidden = 0 AND (
                b.title LIKE ? OR
                b.description LIKE ? OR
                s.name LIKE ?
            )
            ORDER BY b.created_at DESC LIMIT 25;
        """, (query_term, query_term, query_term))
        results["books"] = [dict(r) for r in await cursor.fetchall()]

    return results

# --- Settings & Activity Logs ---
async def get_setting(key: str, default: str = "") -> str:
    async with get_db() as db:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key = ?;", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default

async def set_setting(key: str, value: str) -> None:
    async with get_db() as db:
        await db.execute("""
            INSERT INTO bot_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
        """, (key, value))
        await db.commit()

async def log_activity(user_id: int, action: str, details: Optional[str] = "") -> None:
    async with get_db() as db:
        await db.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?);", (user_id, action, details))
        await db.commit()

async def get_activity_logs(limit: int = 50) -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT l.*, u.full_name, u.username
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.created_at DESC LIMIT ?;
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_statistics() -> Dict[str, int]:
    async with get_db() as db:
        stats = {}
        for table in ["users", "files", "videos", "audios", "books", "schedules", "lectures", "subjects"]:
            cursor = await db.execute(f"SELECT COUNT(*) FROM {table};")
            stats[table] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM files WHERE category = 'ai';")
        stats["ai_files"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM files WHERE category = 'handwritten';")
        stats["handwritten_files"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM files WHERE category = 'powerpoint';")
        stats["ppt_files"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1;")
        stats["banned_users"] = (await cursor.fetchone())[0]

        return stats
