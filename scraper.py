import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DOWNLOAD_DIR = "/tmp"

def download_calendar(username, password, user_id):
    print(f"⬇ شروع دانلود تقویم برای کاربر {user_id} (user_id={user_id})", flush=True)

    user_download_dir = os.path.join(BASE_DOWNLOAD_DIR, str(user_id))
    if not os.path.exists(user_download_dir):
        os.makedirs(user_download_dir)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://courses.aut.ac.ir/calendar/export.php")

        login_provider_xpath = ("//*[@id='region-main']/div[@class='login-wrapper']/div[@class='login-container']/"
                                "div/div[@class='loginform row hastwocolumns']/div[@class='col-lg-6 col-md-12 right-column']/"
                                "div[@class='column-content']/div[@class='login-identityproviders']/a")
        login_provider_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_provider_xpath)))
        login_provider_button.click()

        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_field.clear()
        username_field.send_keys(username)

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(password)

        login_button_xpath = ("//*[@id='fm1']/i[@class='btn btn-block btn-primary btn-submit waves-input-wrapper "
                              "waves-effect waves-float waves-light']/input[@class='waves-button-input']")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()

        wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))

        export_all_button = wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        export_all_button.click()

        timeperiod_button = wait.until(EC.element_to_be_clickable((By.ID, "id_period_timeperiod_recentupcoming")))
        timeperiod_button.click()

        export_button = wait.until(EC.element_to_be_clickable((By.ID, "id_export")))
        export_button.click()

        # صبر برای تکمیل دانلود
        time.sleep(4)

        downloaded_files = [f for f in os.listdir(user_download_dir) if f.endswith(".ics")]
        
        # بررسی فایل‌های دانلود شده
        if not downloaded_files:
            print("❌ هیچ فایل ICS برای این کاربر پیدا نشد یا دانلود نشد.", flush=True)
            return None
        else:
            print(f"📂 فایل‌های موجود برای پردازش: {downloaded_files}", flush=True)

        return user_download_dir

    except Exception as e:
        print(f"❌ خطا در دانلود/ذخیره تقویم: {e}", flush=True)
        return None

    finally:
        driver.quit()
