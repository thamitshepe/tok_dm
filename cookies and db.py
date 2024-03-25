import logging
import pickle
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up database
engine = create_engine('sqlite:///tiktok.db')
Base = declarative_base()

# Define ORM classes for User and SentUser
class User(Base):
    __tablename__ = 'users'
    username = Column(String, unique=True, primary_key=True)

class SentUser(Base):
    __tablename__ = 'sent_users'
    username = Column(String, unique=True, primary_key=True)

# Create tables
Base.metadata.create_all(engine)


# Function to save session cookies
def save_cookies(driver):
    cookies = driver.get_cookies()
    with open("tiktok_cookies.pkl", "wb") as file:
        pickle.dump(cookies, file)
    logging.info("Cookies saved successfully.")

# Function to load cookies
def load_cookies(driver):
    try:
        with open("tiktok_cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            
            for cookie in cookies:
                cookie['domain'] = '.tiktok.com'
                try:
                    driver.add_cookie(cookie)
                    logging.info("Cookie added successfully: %s", cookie)
                except Exception as e:
                    logging.error("Error adding cookie: %s", e)
                    
        logging.info("Loaded existing cookies.")
        return True
    except FileNotFoundError:
        logging.info("Cookies file not found.")
        return False

# Function to check if user is logged in
def is_logged_in(driver):
    try:
        # Wait for the logged-in indicator to appear
        wait = WebDriverWait(driver, 25)
        logged_in_indicator = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-15iwytd-DivProfileContainer.efubjyv0")))
        return True
    except Exception:
        logging.info("Logged in indicator not found. User is not logged in.")
        return False

def initialize_browser():
    # Use webdriver_manager to download and install the compatible ChromeDriver version
    chrome_driver_path = ChromeDriverManager().install()

    # Initialize the Service object with the executable path
    service = Service(executable_path=chrome_driver_path)

    # Initialize the browser
    driver = webdriver.Chrome(service=service)
    return driver

# Function to wait for successful login and redirection to home page
def wait_for_redirect(driver):
    WebDriverWait(driver, 120).until(EC.url_contains("https://www.tiktok.com/foryou?lang=en"))


# Main function
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Initialize the browser
    browser = initialize_browser()
    browser.get("https://www.tiktok.com/login/phone-or-email/email")

    # Fill in the username and password
    username_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-q83gm2-DivInputContainer.etcs7ny0 > input")))
    username_field.send_keys(os.getenv("TIKTOK_USERNAME"))

    password_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-15iauzg-DivContainer.e1bi0g3c0 > div > input")))
    password_field.send_keys(os.getenv("TIKTOK_PASSWORD"))

    # Click the login button
    login_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > button")))
    login_button.click()

    # Wait for the successful login and redirection to home page
    wait_for_redirect(browser)

    # Save session cookies
    save_cookies(browser)

    # Keep the browser open for 100 seconds before finishing
    time.sleep(100)

if __name__ == "__main__":
    main()
