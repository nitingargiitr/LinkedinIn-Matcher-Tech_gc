
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import pickle
import requests
import re
import json
from deepface import DeepFace

MATCH_FILE = "matches_type_new.json"
OUTPUT_FILE = "output.json"
IMAGE_DIR = "images"
COOKIES_FILE = "linkedin_cookies.pkl"
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
PROFILE_PIC_SELECTOR = "img.pv-top-card-profile-picture__image, img.pv-top-card-profile-picture__image--show"

os.makedirs(IMAGE_DIR, exist_ok=True)

def load_cookies(driver, filepath):
    with open(filepath, "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
    print("✅ Cookies loaded.")

def init_browser():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    options.binary_location = BRAVE_PATH
    driver = uc.Chrome(options=options, browser_executable_path=options.binary_location)
    return driver

def clean_name(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_').lower()

def calculate_confidence(distance):
    return max(0, 1 - distance)

def face_exists(image_url):
    try:
        result = DeepFace.extract_faces(image_url, enforce_detection=True)
        return len(result) > 0
    except:
        return False

def compare_faces(img1_url, img2_url):
    try:
        result = DeepFace.verify(img1_url, img2_url, enforce_detection=True)
        if not result["verified"]:
            return calculate_confidence(result["distance"])
        return calculate_confidence(result["distance"])
    except Exception as e:
        print(f"❌ Face comparison error between:\n{img1_url}\n{img2_url}\n➡️ {e}")
        return None

def scrape_and_rank(driver, match_file):
    with open(match_file, 'r') as f:
        match_data = json.load(f)

    output_data = []

    for entry in match_data:
        persona_name = entry.get("persona_name", "unknown")
        url = entry.get("user_image_url")
        input_image_url = gdrive_to_direct_link(url)

        if not input_image_url:
            print(f"[Warning] No valid image URL for persona: {persona_name}")
            input_image_url = None

        elif not face_exists(input_image_url):
            print(f"⚠️ No face found in input image for persona: {persona_name}")
            input_image_url = None

        matches = entry.get("matches", [])[:5]
        print(f"\n🔍 Persona: {persona_name} | Matches: {len(matches)}")

        new_matches = []

        for match in matches:
            profile_url = match["url"]
            driver.get(profile_url.split("?")[0])
            time.sleep(2)

            try:
                name_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                )
                profile_name = name_element.text.strip()
                print(f"➡️ Checking profile: {profile_name}")
            except:
                print("⚠️ Could not extract profile name.")
                match["face_confidence"] = None
                new_matches.append(match)
                continue

            try:
                img = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, PROFILE_PIC_SELECTOR))
                )
                img_url = img.get_attribute("src")

                if not face_exists(img_url):
                    print(f"❌ No face detected in: {img_url}")
                    match["face_confidence"] = None
                else:
                    confidence = compare_faces(input_image_url, img_url) if input_image_url else None
                    match["face_confidence"] = round(confidence, 4) if confidence is not None else None

            except Exception as e:
                print(f"❌ Failed to extract image or compare for {persona_name}: {e}")
                match["face_confidence"] = None

            new_matches.append(match)

        new_matches.sort(key=lambda x: (x.get("face_confidence") is not None, x.get("face_confidence", 0)), reverse=True)
        output_data.append({
            "persona_name": persona_name,
            "input_image_url": input_image_url,
            "matches": new_matches
        })

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\n✅ Finished. Results saved to {OUTPUT_FILE}")

def gdrive_to_direct_link(url):
    if not url:
        return None
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?id={file_id}"
    return url

def main():
    driver = init_browser()
    driver.get("https://www.linkedin.com/")
    time.sleep(3)

    if not os.path.exists(COOKIES_FILE):
        print("❌ Cookies not found. Run profile_pic.py to generate cookies first.")
        driver.quit()
        return

    load_cookies(driver, COOKIES_FILE)
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)

    scrape_and_rank(driver, MATCH_FILE)
    driver.quit()

if __name__ == "__main__":
    main()
