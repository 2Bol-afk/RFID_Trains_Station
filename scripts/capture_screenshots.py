#!/usr/bin/env python3
"""Capture portfolio screenshots from a locally running demo instance."""

import os
import time
from pathlib import Path
from urllib.parse import quote, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get(
    "SCREENSHOT_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")
OUTPUT_DIR = ROOT / "docs" / "assets" / "screenshots"
VIEWPORT = {"width": 1440, "height": 900}


def wait_for_page(driver, heading_text):
    wait = WebDriverWait(driver, 15)
    wait.until(lambda current: current.execute_script("return document.readyState") == "complete")
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(normalize-space(), {heading_text!r})]")
        )
    )
    driver.execute_script(
        "return document.fonts ? document.fonts.ready : Promise.resolve();"
    )
    time.sleep(0.6)


def visit_and_capture(driver, path, filename, heading_text):
    driver.get(f"{BASE_URL}{path}")
    wait_for_page(driver, heading_text)
    output_path = OUTPUT_DIR / filename
    driver.save_screenshot(output_path)
    print(f"Captured {output_path.relative_to(ROOT)}")


def login(driver, username, password, next_path):
    encoded_next = quote(next_path, safe="/")
    driver.get(f"{BASE_URL}/accounts/login/?next={encoded_next}")
    wait = WebDriverWait(driver, 15)
    wait.until(EC.visibility_of_element_located((By.ID, "id_username"))).send_keys(username)
    driver.find_element(By.ID, "id_password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(
        lambda current: urlparse(current.current_url).path.rstrip("/")
        == next_path.rstrip("/")
    )


def build_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Emulation.setDeviceMetricsOverride",
        {
            **VIEWPORT,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    return driver


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    driver = build_driver()
    try:
        visit_and_capture(driver, "/", "home.png", "Choose Your Interface")
        visit_and_capture(
            driver,
            "/passenger/",
            "passenger.png",
            "Passenger Tap Simulator",
        )

        login(
            driver,
            "cashier",
            os.environ.get("SCREENSHOT_CASHIER_PASSWORD", "cashier123"),
            "/cashier/",
        )
        visit_and_capture(
            driver,
            "/cashier/",
            "cashier.png",
            "Cashier Operations",
        )
    finally:
        driver.quit()

    driver = build_driver()
    try:
        login(
            driver,
            "admin",
            os.environ.get("SCREENSHOT_ADMIN_PASSWORD", "admin123"),
            "/admin-dashboard/",
        )
        visit_and_capture(
            driver,
            "/admin-dashboard/",
            "admin-dashboard.png",
            "Admin Dashboard",
        )
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
