import os
import mysql.connector
from db_config import get_db_config
from icalendar import Calendar
from datetime import datetime

BASE_DOWNLOAD_DIR = "/tmp"

def save_ics_to_db(user_id):
    ics_dir = os.path.join(BASE_DOWNLOAD_DIR, str(user_id))
    files = [f for f in os.listdir(ics_dir) if f.endswith(".ics")]
    if not files:
        print("هیچ فایل ICS برای این کاربر پیدا نشد.")
        return

    db_config = get_db_config()
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for file in files:
        full_path = os.path.join(ics_dir, file)
        with open(full_path, "rb") as f:
            gcal = Calendar.from_ical(f.read())
            for component in gcal.walk():
                if component.name == "VEVENT":
                    uid = str(component.get("UID"))
                    summary = str(component.get("SUMMARY") or "بدون عنوان")
                    description = str(component.get("DESCRIPTION") or "بدون توضیحات")
                    category = str(component.get("CATEGORIES") or "نامشخص")
                    dtend = component.get("DTEND")

                    end_time = dtend.dt.strftime('%Y-%m-%d %H:%M:%S') if dtend and isinstance(dtend.dt, datetime) else None

                    try:
                        cursor.execute("""
                            INSERT INTO calendar (uid, user_id, summary, description, end_time, category, is_completed)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE summary=%s, description=%s, end_time=%s, category=%s
                        """, (uid, user_id, summary, description, end_time, category, 0,
                              summary, description, end_time, category))
                    except mysql.connector.Error as err:
                        print(f"❌ خطا در UID={uid}: {err}")

        os.remove(full_path)
        print(f"🧹 فایل {file} با موفقیت حذف شد.")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ ذخیره اطلاعات در دیتابیس کامل شد.")
