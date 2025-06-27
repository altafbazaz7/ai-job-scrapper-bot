import time
import random
import requests
import schedule
import logging
import re
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -------- CONFIG --------
job_roles = [
    "react developer",
    "mern stack developer",
    "full stack developer",
    "frontend developer",
    "react typescript",
    "next js"
]
max_pages = 3
webhook_url = "https://discord.com/api/webhooks/1387047250999382129/SsbSbjfJwfOePob-e3Ox5HAsgQ6zykxqCMhpgGoS2DcbYrDPIpJ9cfLxjgPH0Pgo6n_s"
NODE_SERVER_URL = "http://localhost:3000/evaluate"
MONGO_URI = "mongodb+srv://altafbazaz7:Reactjs123@cluster0.h5qdtmi.mongodb.net/jobbot?retryWrites=true&w=majority"
DB_NAME = "job_bot"
COLLECTION_NAME = "sent_jobs"
LOG_FILE = "job_bot.log"
# ------------------------

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Mongo setup
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
sent_jobs_col = db[COLLECTION_NAME]

def has_been_sent(href):
    doc = sent_jobs_col.find_one({"url": href})
    if doc:
        return str(doc["_id"])
    return None

def save_sent_job(href, score):
    result = sent_jobs_col.insert_one({"url": href, "score": score, "timestamp": time.time()})
    logging.info(f"Saved job to DB: {href} with score {score}, ID: {result.inserted_id}")
    return str(result.inserted_id)

def get_match_score_via_node(job_text):
    try:
        resp = requests.post(NODE_SERVER_URL, json={"job_text": job_text})
        if resp.status_code != 200:
            logging.warning(f"Node server error: {resp.text}")
            return 0
        reply = resp.json().get("reply", "").strip()
        logging.info(f"Raw node reply: {reply}")
        match = re.search(r'\b([1-9]|10)\b', reply)
        if match:
            return int(match.group(1))
        else:
            logging.warning(f"Could not parse valid score from: {reply}")
            return 0
    except Exception as e:
        logging.error(f"Failed to get score from Node server: {e}")
        return 0

def get_label(score):
    if score >= 7:
        return "🔥 HOT"
    elif 5 <= score <= 6:
        return "👍 OK"
    else:
        return "🤔 CAN TRY"



def run_bot():
    logging.info("Bot run started.")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 10)

    try:
        for role in job_roles:
            query = role.replace(" ", "-")
            base_url = f"https://www.naukri.com/{query}-jobs-{{}}?k={query}&jobAge=1&wfhType=2&ctcFilter=15to25&ctcFilter=25to50"

            for page in range(1, max_pages + 1):
                url = base_url.format(page)
                driver.get(url)
                time.sleep(random.uniform(3, 5))

                job_links = driver.find_elements(By.CSS_SELECTOR, "a.title")
                for link in job_links:
                    href = link.get_attribute("href")
                    title = link.text
                    if not href:
                        continue

                    existing_id = has_been_sent(href)
                    if existing_id:
                        message = f"⚠️ Duplicate job from DB — ID: {existing_id}\n{href}"
                        logging.info(message)
                        # Send duplicate alert (even if it was a low score)
                        requests.post(webhook_url, json={"content": message})
                        continue

                    logging.info(f"New job: {href}")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(random.uniform(3, 5))

                    try:
                        jd_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".styles_job-desc-container__txpYf")))
                        job_text = jd_element.text

                        score = get_match_score_via_node(job_text)
                        label = get_label(score)

                        logging.info(f"Score: {score} ({label}) for job {href}")

                        save_sent_job(href, score)

                        if score >= 7:
                            message = f"🧠 **{role.upper()} JOB**\nTitle: {title}\nScore: {score}/10 {label}\n{href}"
                            requests.post(webhook_url, json={"content": message})
                            logging.info(f"Sent HOT job to Discord: {href}")
                        else:
                            logging.info(f"Not HOT (score {score}), not sent to Discord: {href}")

                    except Exception as e:
                        logging.error(f"Error extracting job {href}: {e}")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(random.uniform(1, 2))

    finally:
        driver.quit()
        logging.info("Bot run finished.")



# Schedule every 2 hours
schedule.every(2).hours.do(run_bot)

# Run once at start
run_bot()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)
