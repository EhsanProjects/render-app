# from selenium.webdriver.common.keys import Keys
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait, Select
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# from datetime import datetime
# import time
# import re
import os
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
# pip install xhtml2pdf pandas openpyxl
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import undetected_chromedriver as uc
import re
import shutil



def get_commission(employee_id, password, start_date=None, end_date=None):
    print("Starting Selenium session...")
  
    options = uc.ChromeOptions()
  
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Optional: Use Render environment variable
   # ✅ Explicitly set path to Chrome binary
    chrome_path = "/usr/bin/google-chrome"
    print("Chrome path:", shutil.which("google-chrome"))
    driver = uc.Chrome(options=options, browser_executable_path=chrome_path, use_subprocess=True)


    # driver = uc.Chrome(version_main=135, options=options)
    
    print("Browser started.")
    try:
        print("Loading login page...")
        driver.get("https://hr.macys.net/insite/compensation/fem_review.aspx")

        print("Page loaded. Attempting login...")
        # Wait and input username
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "idToken2"))
        ).send_keys(employee_id)

        # Wait and input password
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "idToken3"))
        ).send_keys(password)

        # Click login button
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "loginButton_0"))
        ).click()

        # Wait for page transition after login
        WebDriverWait(driver, 20).until_not(
            EC.presence_of_element_located((By.ID, "loginButton_0"))
        )
        print("Login successful.")

        # Reset to default content in case of frame switches
        driver.switch_to.default_content()

        # Wait for dropdown to appear
        print("Waiting for dropdown...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "lbStmtDate"))
        )
        print("Dropdown found!")

        # Parse date filters
        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y")

        commissions = []

        # Fetch dropdown options
        select_elem = Select(driver.find_element(By.NAME, "lbStmtDate"))
        all_dates = [opt.text.strip() for opt in select_elem.options]

        for date_text in all_dates:
            try:
                option_date = datetime.strptime(date_text, "%m/%d/%Y")
            except ValueError:
                print("Skipping invalid date format:", date_text)
                continue

            if start_date and option_date < start_date:
                print(f"Skipping {date_text} — before start date.")
                continue
            if end_date and option_date > end_date:
                print(f"Skipping {date_text} — after end date.")
                continue

            print(f"Fetching commission for {date_text}...")

            # Re-locate dropdown each time to avoid stale reference
            select_elem = Select(driver.find_element(By.NAME, "lbStmtDate"))
            select_elem.select_by_visible_text(date_text)

            # Wait for commission data to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'YOUR COMMISSION PAY FOR THE WEEK IS')]"))
            )

            # html = driver.page_source
            # match = re.search(
            #     r"YOUR COMMISSION PAY FOR THE WEEK IS.*?\$([\d,]+\.\d{2})",
            #     html, re.IGNORECASE | re.DOTALL
            # )

            # if match:
            #     amount = re.sub(r"[^\d.]", "", match.group(1))
            #     commissions.append({"date": date_text, "amount": amount})
            #     print(f"✔️  {date_text}: ${amount}")
            # else:
            #     print(f"⚠️  No commission found for {date_text}")


            # ******************************************************
            html = driver.page_source

            # Extract commission from raw HTML (regex still fine here)
            commission_match = re.search(
                r"YOUR COMMISSION PAY FOR THE WEEK IS.*?\$([\d,]+\.\d{2})",
                html, re.IGNORECASE | re.DOTALL
            )

            productive_hours = 0.0
            

            # productive hours-(DOM-based parsing using XPath or element search)
            try:
                # Extract 'Productive Hours' via rendered DOM
                elements = driver.find_elements(By.XPATH, "//*[contains(., 'Productive Hours') and not(self::script or self::style)]")
                for el in elements:
                    text = el.text.strip()
                    print("🔎 Found element text:", text)  # Debug print
                    match = re.search(r"Productive Hours:\s*([\d]+\.\d+)", text)
                    # match = re.search(r"([\d]+\.\d+)", text)
                    if match:
                        productive_hours = float(match.group(1))
                        break
            except Exception as ex:
                print("⚠️ Failed to extract productive hours via DOM:", ex)

            if commission_match:
                amount = re.sub(r"[^\d.]", "", commission_match.group(1))
                # Default if productive hours not found
                # productive_hours = float(hours_match.group(1)) if hours_match else 0.0
                # print("hours: ",hours_match)
                # print("hourssss: ",productive_hours)
                # print("html: ", html)
                commissions.append({
                    "date": date_text,
                    "amount": amount,
                    "productive_hours": productive_hours
                })
                print(f"✔️  {date_text}: ${amount} | Hours: {productive_hours}")
            else:
                print(f"⚠️  No commission found for {date_text}")


            # *******************************************************


        return commissions if commissions else [{"date": "No commission data found", "amount": "0", "productive_hours":"0"}]

    except Exception as e:
        print("🚨 Unexpected error:", e)
        driver.save_screenshot("error_unexpected.png")
        return [{"date": "Error", "amount": str(e)}]

    finally:
        driver.quit()
