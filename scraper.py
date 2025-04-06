import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException, TimeoutException, ElementClickInterceptedException
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
            if files is None:
                print("⚠️ Warning: os.listdir returned None", flush=True)
                return []
            print(f"📑 Raw directory contents: {files}", flush=True)
            return files
        except PermissionError:
            print(f"🚫 Permission denied when accessing directory: {directory}", flush=True)
            return []
        except Exception as e:
            print(f"⚠️ Unexpected error while listing directory: {str(e)}", flush=True)
            return []
            
    except Exception as e:
        print(f"🚨 خطا هنگام لیست کردن پوشه {directory}: {e}", flush=True)
        return []

def wait_and_find_element(driver, by, value, timeout=20, click=False, send_keys=None, check_visibility=False):
    """Enhanced helper function to wait for and interact with elements"""
    try:
        wait = WebDriverWait(driver, timeout)
        
        # First check for presence
        if check_visibility:
            element = wait.until(EC.visibility_of_element_located((by, value)))
        else:
            element = wait.until(EC.presence_of_element_located((by, value)))
            
        if element is None:
            print(f"⚠️ Element {value} not found", flush=True)
            return None
            
        # Wait for element to be clickable if we need to interact with it
        if click or send_keys is not None:
            try:
                element = wait.until(EC.element_to_be_clickable((by, value)))
            except TimeoutException:
                print(f"⚠️ Element {value} is not clickable", flush=True)
                # Try to scroll element into view
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                
        if click:
            try:
                element.click()
            except ElementClickInterceptedException:
                print(f"⚠️ Click intercepted for {value}, trying JavaScript click", flush=True)
                driver.execute_script("arguments[0].click();", element)
                
        if send_keys is not None:
            element.clear()
            element.send_keys(send_keys)
            
        return element
    except TimeoutException:
        print(f"⚠️ Timeout waiting for element {value}", flush=True)
        return None
    except Exception as e:
        print(f"⚠️ Error interacting with element {value}: {str(e)}", flush=True)
        return None

def verify_login_success(driver):
    """Verify login success and handle potential redirects"""
    try:
        # First check if we're still on the login page
        error_messages = driver.find_elements(By.CLASS_NAME, "alert-danger")
        if error_messages:
            for msg in error_messages:
                if msg.is_displayed():
                    print(f"⚠️ Login error message found: {msg.text}", flush=True)
                    return False

        # Check for login success indicators
        success_indicators = [
            "id_events_exportevents_all",  # Calendar export page
            "user-menu",  # User menu in header
            "usermenu",  # Alternative user menu class
            "usertext"   # Username display
        ]

        for indicator in success_indicators:
            element = driver.find_elements(By.ID, indicator) or driver.find_elements(By.CLASS_NAME, indicator)
            if element and any(e.is_displayed() for e in element):
                print(f"✅ Login verified with indicator: {indicator}", flush=True)
                return True

        # If no success indicators found, check current URL
        current_url = driver.current_url
        print(f"📍 Current URL after login: {current_url}", flush=True)
        
        if "login" in current_url.lower():
            print("⚠️ Still on login page", flush=True)
            return False
            
        return True
        
    except Exception as e:
        print(f"⚠️ Error verifying login: {str(e)}", flush=True)
        return False

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

        print("🚀 ورود به سایت...", flush=True)
        driver.get("https://courses.aut.ac.ir/calendar/export.php")
        time.sleep(3)  # Increased initial wait time
        
        print("📄 Verifying page load...", flush=True)
        if not wait_and_find_element(driver, By.TAG_NAME, "body", check_visibility=True):
            raise ConnectionError("Failed to load page")

        login_provider_xpath = ("//*[@id='region-main']/div[@class='login-wrapper']/div[@class='login-container']/"
                              "div/div[@class='loginform row hastwocolumns']/div[@class='col-lg-6 col-md-12 right-column']/"
                              "div[@class='column-content']/div[@class='login-identityproviders']/a")
        print("🔍 Looking for login provider button...", flush=True)
        if not wait_and_find_element(driver, By.XPATH, login_provider_xpath, click=True, check_visibility=True):
            raise ConnectionError("Login provider button not found or not clickable")

        print("✍️ Entering credentials...", flush=True)
        if not wait_and_find_element(driver, By.ID, "username", send_keys=username, check_visibility=True):
            raise ConnectionError("Username field not found")

        if not wait_and_find_element(driver, By.ID, "password", send_keys=password, check_visibility=True):
            raise ConnectionError("Password field not found")

        login_button = wait_and_find_element(driver, By.XPATH, "//*[@id='fm1']//input[@type='submit']", 
                                           click=True, check_visibility=True)
        if not login_button:
            raise ConnectionError("Login button not found or not clickable")

        # Wait longer after login and verify
        time.sleep(5)
        
        print("🔐 Verifying login success...", flush=True)
        if not verify_login_success(driver):
            raise Exception("❌ نام کاربری یا رمز عبور نادرست است.")

        # Try to navigate to calendar export page if not already there
        current_url = driver.current_url
        target_url = "https://courses.aut.ac.ir/calendar/export.php"
        if current_url != target_url:
            print(f"📍 Navigating to calendar export page...", flush=True)
            driver.get(target_url)
            time.sleep(3)

        print("📅 Configuring calendar export...", flush=True)
        export_all = wait_and_find_element(driver, By.ID, "id_events_exportevents_all", click=True, check_visibility=True)
        if not export_all:
            # Try refreshing the page
            print("🔄 Refreshing page...", flush=True)
            driver.refresh()
            time.sleep(3)
            export_all = wait_and_find_element(driver, By.ID, "id_events_exportevents_all", click=True, check_visibility=True)
            if not export_all:
                raise ConnectionError("Export all button not found or not clickable")

        if not wait_and_find_element(driver, By.ID, "id_period_timeperiod_recentupcoming", click=True, check_visibility=True):
            raise ConnectionError("Time period button not found or not clickable")

        if not wait_and_find_element(driver, By.ID, "id_export", click=True, check_visibility=True):
            raise ConnectionError("Export button not found or not clickable")

        print("⌛ در انتظار دانلود فایل...", flush=True)

        timeout_value = 45
        downloaded_files = []
        for i in range(timeout_value):
            print(f"🔄 Checking download status - Attempt {i + 1}/{timeout_value}", flush=True)
            time.sleep(1)
            
            all_files = safe_listdir(user_download_dir)
            if not all_files:
                continue
                
            print(f"⏳ تلاش {i + 1}/{timeout_value} - فایل‌های موجود: {all_files}", flush=True)
            
            downloaded_files = [f for f in all_files if f.endswith(".ics")]
            if downloaded_files:
                break

        if not downloaded_files:
            print("📁 Final directory check...", flush=True)
            final_files = safe_listdir(user_download_dir)
            print(f"📑 Final directory contents: {final_files}", flush=True)
            raise Exception("❌ هیچ فایل .ics پیدا نشد! احتمالاً دانلود شکست خورده.")
        
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