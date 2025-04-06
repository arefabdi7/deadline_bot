import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def download_calendar(username, password, user_id):
    # تعیین دایرکتوری دانلود مخصوص هر کاربر
    base_download_dir = os.path.abspath("/tmp")
    user_download_dir = os.path.join(base_download_dir, str(user_id))
    if not os.path.exists(user_download_dir):
        os.makedirs(user_download_dir)
    
    # تنظیم گزینه‌های Chrome
    chrome_options = Options()
    # برای افزایش سرعت، حالت headless را فعال کنید:
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    
    # تنظیمات دانلود برای Chrome
    prefs = {
        "download.default_directory": user_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # ایجاد instance مرورگر
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 5)
    
    try:
        # رفتن به آدرس سایت
        driver.get("https://courses.aut.ac.ir/calendar/export.php")
        
        # کلیک روی دکمه ورود از طریق کلیک بر روی لینک ارائه دهنده هویت
        login_provider_xpath = ("//*[@id='region-main']/div[@class='login-wrapper']/div[@class='login-container']/"
                                  "div/div[@class='loginform row hastwocolumns']/div[@class='col-lg-6 col-md-12 right-column']/"
                                  "div[@class='column-content']/div[@class='login-identityproviders']/a")
        login_provider_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_provider_xpath)))
        login_provider_button.click()
        
        # پر کردن فیلدهای نام کاربری و رمز عبور
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_field.clear()
        username_field.send_keys(username)
        
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(password)
        
        # کلیک روی دکمه ورود
        login_button_xpath = ("//*[@id='fm1']/i[@class='btn btn-block btn-primary btn-submit waves-input-wrapper waves-effect "
                              "waves-float waves-light']/input[@class='waves-button-input']")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()
        
        # استفاده از انتظارهای مناسب به جای sleep برای تکمیل ورود
        wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        
        # کلیک روی دکمه نمایش همه رویدادها
        export_all_button = wait.until(EC.element_to_be_clickable((By.ID, "id_events_exportevents_all")))
        export_all_button.click()
        
        # کلیک روی دکمه انتخاب بازه زمانی (نمایش رویدادهای اخیر و آینده)
        timeperiod_button = wait.until(EC.element_to_be_clickable((By.ID, "id_period_timeperiod_recentupcoming")))
        timeperiod_button.click()
        
        # کلیک روی دکمه خروجی (Download)
        export_button = wait.until(EC.element_to_be_clickable((By.ID, "id_export")))
        export_button.click()
        
        # صبر کوتاهی جهت تکمیل دانلود (در صورت نیاز می‌توانید این زمان را کاهش یا افزایش دهید)
        time.sleep(3)
        
        print("دانلود فایل تکمیل شد. فایل در مسیر زیر ذخیره شده است:")
        print(user_download_dir)
        
    except Exception as e:
        print("خطایی رخ داده است:", e)
    finally:
        driver.quit()

# نمونه فراخوانی تابع (با جایگزینی نام کاربری و رمز عبور واقعی)
if __name__ == '__main__':
    download_calendar("arefabdi", "Arefabdi1382", 123)
