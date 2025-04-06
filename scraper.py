import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def safe_listdir(directory):
    try:
        # Add debug logging for directory status
        print(f"🔍 Checking directory contents of: {directory}", flush=True)
        print(f"📂 Directory exists: {os.path.exists(directory)}", flush=True)
        if os.path.exists(directory):
            print(f"📝 Directory permissions: {oct(os.stat(directory).st_mode)[-3:]}", flush=True)
        
        files = os.listdir(directory)
        if files is None:
            return []
        return files
    except Exception as e:
        print(f"🚨 خطا هنگام لیست کردن پوشه {directory}: {e}", flush=True)
        return []

def download_calendar(username, password, user_id):
    base_download_dir = "/tmp"
    user_download_dir = os.path.join(base_download_dir, str(user_id))

    if not os.path.exists(user_download_dir):
        os.makedirs(user_download_dir)
        print(f"📁 ساخت پوشه: {user_download_dir}", flush=True)
        print(f"📂 Directory created successfully: {os.path.exists(user_download_dir)}", flush=True)
    else:
        print(f"📁 پوشه قبلاً وجود داشت: {user_download_dir}", flush=True)

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    # Add new security-related options
    options.add_argument("--disable-extensions")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")

    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,  # Added to prevent popups
        "download.default_directory": user_download_dir  # Ensure download path is set
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        print("🚀 ورود به سایت...", flush=True)
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

        login_button_xpath = ("//*[@id='fm1']//input[@type='submit']")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()

        try:
            wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        except Exception:
            raise Exception("❌ نام کاربری یا رمز عبور نادرست است.")
        
        export_all_button = wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        export_all_button.click()

        timeperiod_button = wait.until(EC.element_to_be_clickable((By.ID, "id_period_timeperiod_recentupcoming")))
        timeperiod_button.click()

        export_button = wait.until(EC.element_to_be_clickable((By.ID, "id_export")))
        export_button.click()

        print("⌛ در انتظار دانلود فایل...", flush=True)

        # Increased timeout from 15 to 30 seconds
        timeout = 30
        downloaded_files = []
        for i in range(timeout):
            # Add debug logging before checking files
            print(f"🔄 Checking download status - Attempt {i + 1}/{timeout}", flush=True)
            
            all_files = safe_listdir(user_download_dir)
            print(f"⏳ تلاش {i + 1}/{timeout} - فایل‌های موجود: {all_files}", flush=True)
            
            downloaded_files = [f for f in all_files if f.endswith(".ics")]
            if downloaded_files:
                break
            time.sleep(1)

        if not downloaded_files:
            raise Exception("❌ هیچ فایل .ics پیدا نشد! احتمالاً دانلود شکست خورده.")
        else:
            print("✅ فایل‌های دانلود شده:", downloaded_files, flush=True)
            return True

    except Exception as e:
        print("🚨 خطا هنگام دانلود:", e, flush=True)
        raise e
    finally:
        driver.quit()