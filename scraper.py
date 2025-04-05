import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def download_calendar(username, password, user_id):
    base_download_dir = "/tmp"
    user_download_dir = os.path.join(base_download_dir, str(user_id))

    if not os.path.exists(user_download_dir):
        os.makedirs(user_download_dir)
        print(f"📁 ساخت پوشه: {user_download_dir}")
    else:
        print(f"📁 پوشه قبلاً وجود داشت: {user_download_dir}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 5)

    try:
        print("🚀 ورود به سایت...")
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

        login_button_xpath = ("//*[@id='fm1']/i[@class='btn btn-block btn-primary btn-submit waves-input-wrapper waves-effect "
                              "waves-float waves-light']/input[@class='waves-button-input']")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()

        wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))

        export_all_button = wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        export_all_button.click()

        timeperiod_button = wait.until(EC.element_to_be_clickable((By.ID, "id_period_timeperiod_recentupcoming")))
        timeperiod_button.click()

        export_button = wait.until(EC.element_to_be_clickable((By.ID, "id_export")))
        export_button.click()

        print("⌛ در انتظار دانلود فایل...")

        # چک کردن دانلود تا ۱۵ ثانیه
        timeout = 15
        downloaded_files = []
        for i in range(timeout):
            all_files = os.listdir(user_download_dir)
            print(f"⏳ تلاش {i + 1}/{timeout} - فایل‌های موجود: {all_files}")
            downloaded_files = [f for f in all_files if f.endswith(".ics")]
            if downloaded_files:
                break
            time.sleep(1)

        if not downloaded_files:
            print("❌ هیچ فایل .ics پیدا نشد! احتمالاً دانلود شکست خورده.")
        else:
            print("✅ فایل‌های دانلود شده:", downloaded_files)

    except Exception as e:
        print("🚨 خطا هنگام دانلود:", e)
    finally:
        driver.quit()

if __name__ == '__main__':
    download_calendar("arefabdi", "Arefabdi1382", 123)
