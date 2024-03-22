import time
import pickle
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Set up database
engine = create_engine('sqlite:///tiktok.db')
Base = declarative_base()

# Define ORM class for User
class User(Base):
    __tablename__ = 'users'
    username = Column(String, unique=True, primary_key=True)
    
class SentUser(Base):
    __tablename__ = 'sent_users'
    username = Column(String, unique=True, primary_key=True)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

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

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Initialize the browser
    browser = initialize_browser()
    browser.get("https://www.tiktok.com")

    # Check for existing cookies
    if load_cookies(browser):
        browser.get("https://www.tiktok.com/login/phone-or-email")
        logging.info("Using existing cookies to open TikTok.")

        # Check if the user is logged in
        if is_logged_in(browser):
            logging.info("Logged in successfully.")
        else:
            logging.warning("Logged in with existing cookies but redirected to the login page. Please check if the cookies are valid.")
    else:
        logging.info("No existing cookies found. Please log in manually.")
        browser.get("https://www.tiktok.com/login/phone-or-email")
        logging.info("Please log in manually.")

        # Wait for successful login and redirection to home page
        wait_for_redirect(browser)

        # Save session cookies
        save_cookies(browser)
        
        logging.info("Successfully logged in.")

    time.sleep(8)
    
    # Prompt user to input the hashtag
    hashtag = input("Enter the hashtag you want to scrape: ")
    url = f"https://www.tiktok.com/tag/{hashtag}"
    browser.get(url)
    logging.info("Scraping started from %s.", url)
    
    time.sleep(30)

    # Scroll to load more posts
    for x in range(1, 50):
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print("Scrolling", x)
        time.sleep(15)

    # Find all the usernames and add them to the database without duplicates
    username_elements = WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#main-content-challenge div.css-x6y88p-DivItemContainerV2.e19c29qe8 p.user-name.css-1gi42ki-PUserName.exdlci15")))
    usernames = [element.text.strip() for element in username_elements]


    # Add unique usernames to the database
    for username in set(usernames):
        try:
            user = User(username=username)
            session.add(user)
            session.commit()
            logging.info("Added username '%s' to the database.", username)
        except Exception as e:
            session.rollback()
            logging.warning("Error adding username '%s' to the database: %s", username, e)

    # Close the browser and session
    browser.quit()
    session.close()

if __name__ == "__main__":
    main()
