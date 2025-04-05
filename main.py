import logging
import asyncio
import re
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Database
from scraper import download_calendar
from ics_parser import save_ics_to_db
import pytz
import os
import requests
import jdatetime

print("DATABASE_URL:", os.getenv("DATABASE_URL"))

IRAN_TZ = pytz.timezone('Asia/Tehran')

API_TOKEN = 'توکن خودتو بذار اینجا'

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
db = Database()
scheduler = AsyncIOScheduler()

router = Router()
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(router)

class RegisterState(StatesGroup):
    ask_username = State()
    ask_password = State()

def get_main_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📋 مشاهده ددلاین‌ها")],
        [KeyboardButton(text="✅ فعال‌سازی نوتیف")],
        [KeyboardButton(text="❌ غیرفعالسازی نوتیف")],
        [KeyboardButton(text="🔄 به‌روزرسانی ددلاین‌ها")]
    ])

def clean_title(title):
    return re.sub(r'\s*is due\s*$', '', title, flags=re.IGNORECASE).strip()

def to_persian_date(dt: datetime) -> str:
    dt = dt.astimezone(IRAN_TZ)
    jdt = jdatetime.datetime.fromgregorian(datetime=dt)
    return jdt.strftime('%Y/%m/%d %H:%M')

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    chat_id = message.chat.id
    if db.user_exists(chat_id):
        await message.answer("شما قبلاً ثبت‌نام کرده‌اید. لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=get_main_menu())
    else:
        await state.set_state(RegisterState.ask_username)
        await message.answer("👤 لطفاً نام کاربری دانشگاهی خود را وارد کنید:")

@router.message(RegisterState.ask_username)
async def ask_password(message: Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await state.set_state(RegisterState.ask_password)
    await message.answer("🔒 لطفاً رمز عبور خود را وارد کنید:")

@router.message(RegisterState.ask_password)
async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    password = message.text.strip()
    chat_id = message.chat.id

    db.add_user(chat_id, username, password)
    await message.answer("✅ ثبت‌نام با موفقیت انجام شد. در حال دریافت اطلاعات...")

    await download_and_parse_calendar(chat_id)

    await message.answer("🎉 آماده‌ایم! یکی از گزینه‌های زیر را انتخاب کن:", reply_markup=get_main_menu())
    await state.clear()

@router.message(F.text == '📋 مشاهده ددلاین‌ها')
async def show_deadlines(message: Message):
    chat_id = message.chat.id
    deadlines = db.get_deadlines(chat_id)

    if not deadlines:
        await message.answer("📭 شما هیچ ددلاینی ثبت‌شده ندارید!")
        return
    
    response = "📅 <b>لیست ددلاین‌های شما:</b>\n\n"

    for dl in deadlines:
        title = clean_title(dl.get('title', "بدون عنوان"))
        description = dl.get('description', "بدون توضیحات")
        category = dl.get('category', "نامشخص")
        date = dl.get('date')

        if date and isinstance(date, datetime):
            date = to_persian_date(date)
        else:
            date = "زمان نامشخص"

        response += f"🔹 <b>{title}</b>\n📘 <b>{category}</b>\n📆 <i>{date}</i>\n📝 {description}\n━━━━━━━━━━━━━━━━━━━━━━\n"

    await message.answer(response, parse_mode=ParseMode.HTML)

@router.message(F.text == '✅ فعال‌سازی نوتیف')
async def enable_notif(message: Message):
    chat_id = message.chat.id
    user = db.get_user(chat_id)
    if user and user['is_notif_active']:
        await message.answer("📢 نوتیف قبلاً فعال شده است.")
    else:
        db.set_notif_status(chat_id, True)
        await message.answer("✅ نوتیف با موفقیت فعال شد.")

@router.message(F.text == '❌ غیرفعالسازی نوتیف')
async def disable_notif(message: Message):
    chat_id = message.chat.id
    user = db.get_user(chat_id)
    if user and not user['is_notif_active']:
        await message.answer("🔕 نوتیف قبلاً غیرفعال بوده است.")
    else:
        db.set_notif_status(chat_id, False)
        await message.answer("❌ نوتیف با موفقیت غیرفعال شد.")

@router.message(F.text == '🔄 به‌روزرسانی ددلاین‌ها')
async def manual_update(message: Message):
    chat_id = message.chat.id
    await message.answer("⏳ در حال به‌روزرسانی ددلاین‌ها...")
    await download_and_parse_calendar(chat_id)
    await message.answer("✅ ددلاین‌ها با موفقیت به‌روزرسانی شدند.")

@router.callback_query(F.data.startswith("done:"))
async def mark_done(callback: CallbackQuery):
    uid = callback.data.split(":")[1]
    chat_id = callback.from_user.id
    db.mark_completed(chat_id, uid)
    await callback.answer("✅ با موفقیت ثبت شد. دیگر یادآوری نخواهید گرفت.")

async def download_and_parse_calendar(chat_id):
    user = db.get_user(chat_id)
    if not user:
        print("❌ [download] کاربر یافت نشد:", chat_id)
        return
    try:
        print(f"⬇ شروع دانلود تقویم برای کاربر {user['username']} (user_id={user['user_id']})")
        download_calendar(user['username'], user['password'], user['user_id'])
        print("📂 فایل تقویم با موفقیت دانلود شد.")
        save_ics_to_db(user['user_id'])
        print("✅ ذخیره ددلاین‌ها در دیتابیس با موفقیت انجام شد.")
    except Exception as e:
        print(f"❌ خطا در دانلود/ذخیره تقویم: {e}")

async def delete_expired():
    db.delete_expired_events()

async def send_notifications():
    users = db.get_all_users()
    for chat_id in users:
        user = db.get_user(chat_id)
        if not user or not user['is_notif_active']:
            continue
        events = db.get_upcoming_events(user['user_id'])
        now = datetime.now()
        for event in events:
            delta = event['end_time'] - now
            if delta in [timedelta(days=7), timedelta(days=3), timedelta(days=1), timedelta(hours=12), timedelta(hours=3)]:
                if not db.is_notified(user['user_id'], event['uid'], delta):
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="انجام دادم ✅", callback_data=f"done:{event['uid']}")]
                    ])
                    end_time_str = to_persian_date(event['end_time'])
                    await bot.send_message(
                        chat_id,
                        f"⏰ یادآوری: <b>{clean_title(event['summary'])}</b>\n📘 <b>{event['category']}</b>\n📆 <i>{end_time_str}</i>\n📝 {event['description']}",
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup
                    )
                    db.mark_as_notified(user['user_id'], event['uid'], delta)

async def periodic_tasks():
    users = db.get_all_users()
    for chat_id in users:
        await download_and_parse_calendar(chat_id)
    await delete_expired()

async def main():
    url = f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook"
    response = requests.get(url)
    print(f"Webhook deleted: {response.json()}")

    scheduler.add_job(periodic_tasks, 'interval', hours=1)
    scheduler.add_job(send_notifications, 'interval', minutes=15)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
