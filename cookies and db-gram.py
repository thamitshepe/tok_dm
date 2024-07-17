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
engine = create_engine('sqlite:///instagram.db')
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
    with open("instagram_cookies.pkl", "wb") as file:
        pickle.dump(cookies, file)
    logging.info("Cookies saved successfully.")


def initialize_browser():
    # Use webdriver_manager to download and install the compatible ChromeDriver version
    chrome_driver_path = ChromeDriverManager().install()

    # Initialize the Service object with the executable path
    service = Service(executable_path=chrome_driver_path)

    # Initialize the browser
    driver = webdriver.Chrome(service=service)
    return driver


# Main function
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Initialize the browser
    browser = initialize_browser()
    browser.get("https://www.instagram.com/")

    # Fill in the username and password
    username_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#loginForm > div > div:nth-child(1) > div > label > input")))
    username_field.send_keys(os.getenv("GRAM_USERNAME"))

    password_field = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#loginForm > div > div:nth-child(2) > div > label > input")))
    password_field.send_keys(os.getenv("GRAM_PASSWORD"))

    # Click the login button
    login_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginForm > div > div:nth-child(3) > button")))
    login_button.click()
    
    time.sleep(40)
    
    # Save session cookies
    save_cookies(browser)

    # Keep the browser open for 100 seconds before finishing
    time.sleep(100)

if __name__ == "__main__":
    main()
