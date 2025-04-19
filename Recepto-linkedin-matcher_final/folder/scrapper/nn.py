# save_cookies.py
import undetected_chromedriver as uc
import pickle
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

COOKIES_FILE = "linkedin_cookies.pkl"
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

def init_browser():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.binary_location = BRAVE_PATH
    driver = uc.Chrome(options=options, browser_executable_path=options.binary_location)
    return driver

def save_linkedin_cookies():
    driver = init_browser()
    driver.get("https://www.linkedin.com/login")
    
    print("Please log in to LinkedIn manually in the browser window...")
    
    # Wait until user is logged in (detect feed page)
    WebDriverWait(driver, 300).until(
        EC.url_contains("linkedin.com/feed")
    )
    
    # Save cookies
    with open(COOKIES_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print(f"✅ Cookies saved to {COOKIES_FILE}")
    
    driver.quit()

if __name__ == "__main__":
    save_linkedin_cookies()