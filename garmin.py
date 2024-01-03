import time
from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from api.config import GARMIN_USERNAME, GARMIN_PASSWORD
from selenium.webdriver.support.ui import WebDriverWait

GARMIN_URL = "https://connect.garmin.com/signin"

import time
import random


def send_keys_with_delay(element, text, min_delay=0.005, max_delay=0.01):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))  # pause for a random duration


def login_website(username, password):
    options = Options()
    options.headless = True  # run Firefox in headless mode
    driver = webdriver.Firefox(options=options)

    driver.get(GARMIN_URL)
    time.sleep(3)
    waiter = WebDriverWait(driver, 10)
    waiter.until(lambda driver: driver.find_element(By.NAME, "email"))
    waiter.until(lambda driver: driver.find_element(By.NAME, "email"))

    username_elem = driver.find_element(By.NAME, "email")  # find username field
    send_keys_with_delay(username_elem, username)

    password_elem = driver.find_element(By.NAME, "password")  # find password field
    send_keys_with_delay(password_elem, password)


    driver.find_element(
        By.XPATH, "/html/body/div/main/div[2]/div/div/div/div/form/section[2]/g-button"
    ).click()  # click the login button
    time.sleep(5)

    driver.save_screenshot("screenshot.png")  # save a screenshot of the webpage


login_website(GARMIN_USERNAME, GARMIN_PASSWORD)
