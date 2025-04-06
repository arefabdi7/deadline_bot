import logging
import asyncio
import aiohttp
import re
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import types
from aiogram.exceptions import TelegramConflictError
from db import Database
from scraper import download_calendar
from ics_parser import save_ics_to_db
import pytz
import os
import requests
import jdatetime

print("DATABASE_URL:", os.getenv("DATABASE_URL"), flush=True)

IRAN_TZ = pytz.timezone('Asia/Tehran')
API_TOKEN = '8081419581:AAFVWumPeFKRfonfo-L41hgQmtiWEc8srM4'

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

# Error handler to catch TelegramConflictError and delete webhook immediately
async def telegram_conflict_error_handler(update: types.Update, exception: TelegramConflictError):
    print("TelegramConflictError encountered. Trying to delete webhook immediately...", flush=True)
    try:
        await check_and_delete_webhook()
        print("Webhook deleted via error handler.", flush=True)
    except Exception as exc:
        print(f"Error while deleting webhook in error handler: {exc}", flush=True)
    return True  # Prevent further propagation of the error

# Register error handler without extra keyword arguments
dp.errors.register(telegram_conflict_error_handler)

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

# Asynchronous webhook checking using aiohttp
async def check_and_delete_webhook():
    url = f"https://api.telegram.org/bot{API_TOKEN}/getWebhookInfo"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            print("Webhook Info:", data, flush=True)
            if data.get("result", {}).get("url"):
                print("Webhook is active, deleting it...", flush=True)
                await delete_webhook(session)
                await asyncio.sleep(1)  # Wait to ensure webhook deletion
                async with session.get(url) as resp2:
                    data2 = await resp2.json()
                    print("Webhook Info after deletion:", data2, flush=True)
                    if data2.get("result", {}).get("url"):
                        raise Exception("Failed to delete webhook. Please try again later.")
                    print("Webhook deleted successfully.", flush=True)

async def delete_webhook(session):
    url = f"https://api.telegram.org/bot{API_TOKEN}/deleteWebhook"
    async with session.get(url) as resp:
        data = await resp.json()
        if data.get("ok"):
            print("✅ Webhook deletion response:", data, flush=True)
        else:
            print("❌ Failed to delete webhook:", data, flush=True)

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    print("Received /start command.", flush=True)
    await check_and_delete_webhook()
    chat_id = message.chat.id
    if db.user_exists(chat_id):
        print(f"کاربر {chat_id} موجود است.", flush=True)
        await message.answer("شما قبلاً ثبت‌نام کرده‌اید. لطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup=get_main_menu())
    else:
        print(f"کاربر {chat_id} موجود نیست و نیاز به ثبت‌نام دارد.", flush=True)
        await state.set_state(RegisterState.ask_username)
        await message.answer("👤 لطفاً نام کاربری دانشگاهی خود را وارد کنید:")

@router.message(RegisterState.ask_username)
async def ask_password(message: Message, state: FSMContext):
    username = message.text.strip()
    print(f"Received username: {username}", flush=True)
    await state.update_data(username=username)
    await state.set_state(RegisterState.ask_password)
    await message.answer("🔒 لطفاً رمز عبور خود را وارد کنید:")

@router.message(RegisterState.ask_password)
async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    password = message.text.strip()
    chat_id = message.chat.id

    print(f"Attempting to download calendar for user: {username} (ID: {chat_id})", flush=True)
    await message.answer("در حال دریافت اطلاعات...", flush=True)

    try:
        success = await download_and_parse_calendar(username, password, chat_id)
        if success:
            print("Calendar download and parse succeeded.", flush=True)
            db.add_user(chat_id, username, password)
            await message.answer("✅ ثبت‌نام با موفقیت انجام شد. 🎉 آماده‌ایم! یکی از گزینه‌های زیر را انتخاب کن:", reply_markup=get_main_menu())
            await state.clear()
        else:
            raise Exception("Failed to download and parse calendar")
    except Exception as e:
        print(f"Error during registration: {e}", flush=True)
        db.delete_user(chat_id)
        await state.set_state(RegisterState.ask_username)
        await message.answer(f"❌ خطا در ثبت‌نام: {str(e)}. لطفاً دوباره نام کاربری دانشگاهی خود را وارد کنید:", flush=True)

@router.message(F.text == '📋 مشاهده ددلاین‌ها')
async def show_deadlines(message: Message):
    print(f"User {message.chat.id} requested deadlines.", flush=True)
    await check_and_delete_webhook()
    chat_id = message.chat.id
    db = Database()
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
    print(f"Enabling notifications for user {message.chat.id}", flush=True)
    chat_id = message.chat.id
    user = db.get_user(chat_id)
    if user and user['is_notif_active']:
        await message.answer("📢 نوتیف قبلاً فعال شده است.")
    else:
        db.set_notif_status(chat_id, True)
        await message.answer("✅ نوتیف با موفقیت فعال شد.", flush=True)

@router.message(F.text == '❌ غیرفعالسازی نوتیف')
async def disable_notif(message: Message):
    print(f"Disabling notifications for user {message.chat.id}", flush=True)
    chat_id = message.chat.id
    user = db.get_user(chat_id)
    if user and not user['is_notif_active']:
        await message.answer("🔕 نوتیف قبلاً غیرفعال بوده است.")
    else:
        db.set_notif_status(chat_id, False)
        await message.answer("❌ نوتیف با موفقیت غیرفعال شد.", flush=True)

@router.message(F.text == '🔄 به‌روزرسانی ددلاین‌ها')
async def manual_update(message: Message):
    print(f"User {message.chat.id} requested manual update.", flush=True)
    await check_and_delete_webhook()
    chat_id = message.chat.id
    await message.answer("⏳ در حال به‌روزرسانی ددلاین‌ها...", flush=True)
    await download_and_parse_calendar(username=None, password=None, user_id=chat_id)
    await message.answer("✅ ددلاین‌ها با موفقیت به‌روزرسانی شدند.", flush=True)

@router.callback_query(F.data.startswith("done:"))
async def mark_done(callback: CallbackQuery):
    uid = callback.data.split(":")[1]
    chat_id = callback.from_user.id
    print(f"Marking event {uid} as done for user {chat_id}", flush=True)
    db.mark_completed(chat_id, uid)
    await callback.answer("✅ با موفقیت ثبت شد. دیگر یادآوری نخواهید گرفت.", flush=True)

@router.message(F.text == "/delete")
async def delete_user(message: Message):
    chat_id = message.chat.id
    print(f"Deleting user and deadlines for user {chat_id}", flush=True)
    await delete_user_and_deadlines(chat_id)
    await message.answer("✅ کاربر و ددلاین‌های شما با موفقیت حذف شدند.", flush=True)

async def download_and_parse_calendar(username, password, user_id):
    try:
        print(f"⬇ شروع دانلود تقویم برای کاربر {username or user_id} (user_id={user_id})", flush=True)
        await asyncio.to_thread(download_calendar, username, password, user_id)
        print("📂 فایل تقویم با موفقیت دانلود شد.", flush=True)
        await asyncio.to_thread(save_ics_to_db, user_id)
        print("✅ ذخیره ددلاین‌ها در دیتابیس با موفقیت انجام شد.", flush=True)
        return True
    except Exception as e:
        print(f"❌ خطا در دانلود/ذخیره تقویم: {e}", flush=True)
        return False

async def delete_user_and_deadlines(chat_id):
    db.delete_user(chat_id)
    print(f"کاربر {chat_id} و ددلاین‌هایش حذف شدند.", flush=True)

async def delete_expired():
    db.delete_expired_events()

async def send_notifications():
    users = db.get_all_users()
    intervals = {
        '7d': 7 * 86400,
        '3d': 3 * 86400,
        '1d': 86400,
        '12h': 43200,
        '3h': 10800
    }
    tolerance = 300
    now = datetime.now()
    for chat_id in users:
        user = db.get_user(chat_id)
        if not user or not user['is_notif_active']:
            continue
        events = db.get_upcoming_events(user['user_id'])
        for event in events:
            delta_seconds = (event['end_time'] - now).total_seconds()
            for key, interval in intervals.items():
                if abs(delta_seconds - interval) <= tolerance:
                    if not db.is_notified(user['user_id'], event['uid'], key):
                        markup = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="انجام دادم ✅", callback_data=f"done:{event['uid']}")]
                        ])
                        end_time_str = to_persian_date(event['end_time'])
                        await bot.send_message(
                            chat_id,
                            f"⏰ یادآوری: <b>{clean_title(event['summary'])}</b>\n"
                            f"📘 <b>{event['category']}</b>\n"
                            f"📆 <i>{end_time_str}</i>\n"
                            f"📝 {event['description']}",
                            parse_mode=ParseMode.HTML,
                            reply_markup=markup
                        )
                        db.mark_as_notified(user['user_id'], event['uid'], key)

async def periodic_tasks():
    users = db.get_all_users()
    for chat_id in users:
        await download_and_parse_calendar(username=None, password=None, user_id=chat_id)
    await delete_expired()

async def main():
    print("Starting main function...", flush=True)
    await check_and_delete_webhook()
    # Additional delay to ensure webhook deletion is fully processed
    await asyncio.sleep(5)
    scheduler.add_job(periodic_tasks, 'interval', hours=1)
    scheduler.add_job(send_notifications, 'interval', minutes=5)
    scheduler.add_job(check_and_delete_webhook, 'interval', minutes=0.5)
    scheduler.start()
    print("Scheduler started. Starting polling...", flush=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
