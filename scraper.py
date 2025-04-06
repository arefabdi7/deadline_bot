import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
import urllib3
from urllib3.exceptions import MaxRetryError
import socket
from contextlib import contextmanager
import signal

class ConnectionError(Exception):
    pass

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError()
    
    # Use signal module directly instead of socket.signal
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def retry_on_connection_error(func, max_retries=3, delay=5):
    def wrapper(*args, **kwargs):
        retries = 0
        last_exception = None
        
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except (ConnectionError, WebDriverException, MaxRetryError, socket.error, TimeoutError) as e:
                last_exception = e
                retries += 1
                print(f"🔄 Retry attempt {retries}/{max_retries} after error: {str(e)}", flush=True)
                if retries < max_retries:
                    time.sleep(delay)
        raise last_exception
    return wrapper

def safe_listdir(directory):
    try:
        if not os.path.exists(directory):
            print(f"❌ Directory does not exist: {directory}", flush=True)
            return []
        
        print(f"🔍 Checking directory contents of: {directory}", flush=True)
        print(f"📂 Directory exists: {os.path.exists(directory)}", flush=True)
        print(f"📝 Directory permissions: {oct(os.stat(directory).st_mode)[-3:]}", flush=True)
        
        try:
            files = os.listdir(directory)
            print(f"📑 Raw directory contents: {files}", flush=True)
            return files if files is not None else []
        except PermissionError:
            print(f"🚫 Permission denied when accessing directory: {directory}", flush=True)
            return []
        except Exception as e:
            print(f"⚠️ Unexpected error while listing directory: {str(e)}", flush=True)
            return []
            
    except Exception as e:
        print(f"🚨 خطا هنگام لیست کردن پوشه {directory}: {e}", flush=True)
        return []

def wait_for_element(driver, by, value, timeout=20):
    try:
        wait = WebDriverWait(driver, timeout)
        element = wait.until(EC.presence_of_element_located((by, value)))
        return element
    except Exception as e:
        print(f"⚠️ Error waiting for element {value}: {str(e)}", flush=True)
        return None

@retry_on_connection_error
def download_calendar(username, password, user_id):
    base_download_dir = "/tmp"
    user_download_dir = os.path.join(base_download_dir, str(user_id))

    try:
        if not os.path.exists(user_download_dir):
            os.makedirs(user_download_dir, mode=0o755)
            print(f"📁 ساخت پوشه: {user_download_dir}", flush=True)
            print(f"📂 Directory created successfully: {os.path.exists(user_download_dir)}", flush=True)
            print(f"📝 Created directory permissions: {oct(os.stat(user_download_dir).st_mode)[-3:]}", flush=True)
        else:
            print(f"📁 پوشه قبلاً وجود داشت: {user_download_dir}", flush=True)
    except Exception as e:
        print(f"❌ Error creating directory: {str(e)}", flush=True)
        raise e

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--ignore-certificate-errors")
    
    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "browser.download.manager.showWhenStarting": False,
        "browser.download.manager.focusWhenStarting": False,
        "browser.download.useDownloadDir": True,
        "browser.helperApps.neverAsk.saveToDisk": "text/calendar,application/octet-stream",
        "network.http.connection-timeout": 30000
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        print("🔧 Initializing Chrome driver...", flush=True)
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(30)
        wait = WebDriverWait(driver, 20)

        print("🚀 ورود به سایت...", flush=True)
        driver.get("https://courses.aut.ac.ir/calendar/export.php")
        
        print("📄 Verifying page load...", flush=True)
        body = wait_for_element(driver, By.TAG_NAME, "body")
        if not body:
            raise ConnectionError("Failed to load page")

        login_provider_xpath = ("//*[@id='region-main']/div[@class='login-wrapper']/div[@class='login-container']/"
                              "div/div[@class='loginform row hastwocolumns']/div[@class='col-lg-6 col-md-12 right-column']/"
                              "div[@class='column-content']/div[@class='login-identityproviders']/a")
        print("🔍 Looking for login provider button...", flush=True)
        login_provider_button = wait_for_element(driver, By.XPATH, login_provider_xpath)
        if not login_provider_button:
            raise ConnectionError("Login provider button not found")
        login_provider_button.click()

        print("✍️ Entering credentials...", flush=True)
        username_field = wait_for_element(driver, By.ID, "username")
        if not username_field:
            raise ConnectionError("Username field not found")
        username_field.clear()
        username_field.send_keys(username)

        password_field = wait_for_element(driver, By.ID, "password")
        if not password_field:
            raise ConnectionError("Password field not found")
        password_field.clear()
        password_field.send_keys(password)

        login_button_xpath = "//*[@id='fm1']//input[@type='submit']"
        login_button = wait_for_element(driver, By.XPATH, login_button_xpath)
        if not login_button:
            raise ConnectionError("Login button not found")
        login_button.click()

        try:
            print("🔐 Verifying login success...", flush=True)
            export_all = wait_for_element(driver, By.ID, "id_events_exportevents_all")
            if not export_all:
                raise Exception("❌ نام کاربری یا رمز عبور نادرست است.")
        except Exception as e:
            print(f"❌ Login verification failed: {str(e)}", flush=True)
            raise Exception("❌ نام کاربری یا رمز عبور نادرست است.")
        
        print("📅 Configuring calendar export...", flush=True)
        export_all_button = wait_for_element(driver, By.ID, "id_events_exportevents_all")
        if not export_all_button:
            raise ConnectionError("Export all button not found")
        export_all_button.click()

        timeperiod_button = wait_for_element(driver, By.ID, "id_period_timeperiod_recentupcoming")
        if not timeperiod_button:
            raise ConnectionError("Time period button not found")
        timeperiod_button.click()

        export_button = wait_for_element(driver, By.ID, "id_export")
        if not export_button:
            raise ConnectionError("Export button not found")
        export_button.click()

        print("⌛ در انتظار دانلود فایل...", flush=True)

        timeout_value = 45
        downloaded_files = []
        for i in range(timeout_value):
            print(f"🔄 Checking download status - Attempt {i + 1}/{timeout_value}", flush=True)
            
            all_files = safe_listdir(user_download_dir)
            if not all_files:
                print("⚠️ No files found in directory", flush=True)
                time.sleep(1)
                continue
                
            print(f"⏳ تلاش {i + 1}/{timeout_value} - فایل‌های موجود: {all_files}", flush=True)
            
            downloaded_files = [f for f in all_files if f.endswith(".ics")]
            if downloaded_files:
                break
            time.sleep(1)

        if not downloaded_files:
            print("📁 Final directory check...", flush=True)
            final_files = safe_listdir(user_download_dir)
            print(f"📑 Final directory contents: {final_files}", flush=True)
            raise Exception("❌ هیچ فایل .ics پیدا نشد! احتمالاً دانلود شکست خورده.")
        else:
            print("✅ فایل‌های دانلود شده:", downloaded_files, flush=True)
            return True

    except Exception as e:
        print("🚨 خطا هنگام دانلود:", str(e), flush=True)
        if isinstance(e, (ConnectionError, WebDriverException, MaxRetryError, socket.error, TimeoutError)):
            raise ConnectionError(str(e))
        raise e
    finally:
        if driver:
            try:
                driver.quit()
                print("🚫 Browser closed", flush=True)
            except Exception as e:
                print(f"⚠️ Error closing browser: {str(e)}", flush=True)