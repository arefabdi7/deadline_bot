import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def download_calendar(username, password, user_id):
    # تعیین دایرکتوری دانلود مخصوص هر کاربر
    base_download_dir = os.path.abspath("download")
    user_download_dir = os.path.join(base_download_dir, str(user_id))
    os.makedirs(user_download_dir, exist_ok=True)

    # تنظیم گزینه‌های Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # مسیر منحصر به‌فرد برای داده‌های مرورگر
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{user_id}")

    # تنظیمات دانلود برای Chrome
    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # ایجاد مرورگر
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 5)

    try:
        print(f"⬇ شروع دانلود تقویم برای کاربر {user_id} (user_id={user_id})")
        driver.get("https://courses.aut.ac.ir/calendar/export.php")

        # کلیک روی دکمه ورود با شناسه دانشگاه
        login_provider_xpath = ("//*[@id='region-main']/div[@class='login-wrapper']/div[@class='login-container']/"
                                "div/div[@class='loginform row hastwocolumns']/div[@class='col-lg-6 col-md-12 right-column']/"
                                "div[@class='column-content']/div[@class='login-identityproviders']/a")
        login_provider_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_provider_xpath)))
        login_provider_button.click()

        # پر کردن فیلدهای ورود
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_field.clear()
        username_field.send_keys(username)

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(password)

        login_button_xpath = ("//*[@id='fm1']/i[@class='btn btn-block btn-primary btn-submit waves-input-wrapper waves-effect "
                              "waves-float waves-light']/input[@class='waves-button-input']")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()

        # انتخاب گزینه‌ها و دانلود
        wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "id_period_timeperiod_recentupcoming"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "id_export"))).click()

        time.sleep(3)  # صبر برای کامل شدن دانلود

        print("✅ دانلود فایل تکمیل شد. فایل در مسیر زیر ذخیره شده است:")
        print(user_download_dir)

    except Exception as e:
        print("❌ خطا در دانلود/ذخیره تقویم:", e)
    finally:
        driver.quit()

# تست محلی
if __name__ == '__main__':
    download_calendar("USERNAME", "PASSWORD", 123)
