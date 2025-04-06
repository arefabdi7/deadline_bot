import os
import mysql.connector
from db_config import get_db_config
from icalendar import Calendar
from datetime import datetime

BASE_DOWNLOAD_DIR = "/tmp"

def extract_course_name(category_field):
    if category_field and '-' in category_field:
        parts = category_field.split('-')
        name = parts[-1].strip()
        return name if len(name) > 3 else category_field.strip()
    return category_field.strip() if category_field else "نامشخص"

def save_ics_to_db(user_id):
    ics_dir = os.path.join(BASE_DOWNLOAD_DIR, str(user_id))
    if not os.path.exists(ics_dir):
        print(f"❌ پوشه {ics_dir} وجود ندارد.")
        return

    files = [f for f in os.listdir(ics_dir) if f.endswith(".ics")]
    if not files:
        print("❌ هیچ فایل ICS برای این کاربر پیدا نشد.")
        return

    print("📂 فایل‌های موجود برای پردازش:", files)
    
    db_config = get_db_config()
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for file in files:
        full_path = os.path.join(ics_dir, file)
        print(f"🔎 در حال پردازش فایل: {file}, حجم: {os.path.getsize(full_path)} بایت")
        with open(full_path, "rb") as f:
            gcal = Calendar.from_ical(f.read())
            for component in gcal.walk():
                if component.name == "VEVENT":
                    uid = str(component.get("UID"))
                    summary = str(component.get("SUMMARY") or "بدون عنوان")
                    description = str(component.get("DESCRIPTION") or "بدون توضیحات")
                    
                    raw_category_field = component.get("CATEGORIES")
                    raw_category = str(raw_category_field[0]) if isinstance(raw_category_field, list) else str(raw_category_field)
                    category = extract_course_name(raw_category)

                    dtend = component.get("DTEND")
                    end_time = dtend.dt.strftime('%Y-%m-%d %H:%M:%S') if dtend and isinstance(dtend.dt, datetime) else None

                    try:
                        cursor.execute("""
                            INSERT INTO calendar (uid, user_id, summary, description, end_time, category, is_completed)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE summary=%s, description=%s, end_time=%s, category=%s
                        """, (uid, user_id, summary, description, end_time, category, 0,
                              summary, description, end_time, category))
                        print(f"✅ رویداد با UID={uid} ذخیره شد.")
                    except mysql.connector.Error as err:
                        print(f"❌ خطا در ذخیره UID={uid}: {err}")

        print(f"🧹 حذف فایل {file}")
        os.remove(full_path)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ ذخیره اطلاعات در دیتابیس کامل شد.")
