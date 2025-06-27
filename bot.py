import time
import random
import requests
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
sent_jobs_file = "sent_jobs.txt"
NODE_SERVER_URL = "http://localhost:3000/evaluate"
# ------------------------

def load_sent_jobs():
    try:
        with open(sent_jobs_file, 'r') as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

def save_sent_job(job_url):
    with open(sent_jobs_file, 'a') as f:
        f.write(job_url + "\n")

def get_match_score_via_node(job_text):
    try:
        resp = requests.post(NODE_SERVER_URL, json={"job_text": job_text})
        if resp.status_code != 200:
            print("⚠️ Node server error:", resp.text)
            return 0
        reply = resp.json().get("reply", "").strip()
        score = int(''.join(filter(str.isdigit, reply.split()[0])))
        return score
    except Exception as e:
        print("⚠️ Failed to get score from Node server:", e)
        return 0

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
wait = WebDriverWait(driver, 10)

try:
    while True:
        sent_jobs = load_sent_jobs()

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
                    if not href or href in sent_jobs:
                        continue
                    
                    print(f"➡️ Checking job: {href}")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(random.uniform(3, 5))

                    try:
                        jd_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".styles_job-desc-container__txpYf")))
                        job_text = jd_element.text

                        score = get_match_score_via_node(job_text)

                        print(f"💡 JD Analyzer score: {score}/10")

                        if score > 7:
                            message = (
                                f"🧠 **{role.upper()} JOB**\n"
                                f"Title: {title}\n"
                                f"Score: {score}/10 🔥 HOT\n"
                                f"{href}"
                            )
                            requests.post(webhook_url, json={"content": message})
                            save_sent_job(href)
                        else:
                            print(f"❌ Skipped (score {score})")

                    except Exception as e:
                        print("⚠️ Error extracting job:", e)

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(random.uniform(1, 2))

        print("✅ Hourly run done. Sleeping until next hour.")
        time.sleep(3600)

finally:
    driver.quit()
