import time
import json
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
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
import requests

# Set up database
engine = create_engine('sqlite:///instagram.db')
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
    with open("instagram_cookies.pkl", "wb") as file:
        pickle.dump(cookies, file)
    logging.info("Cookies saved successfully.")

# Function to load cookies
def load_cookies(driver):
    try:
        with open("instagram_cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            
            for cookie in cookies:
                cookie['domain'] = '.instagram.com'
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
        logged_in_indicator = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[2]/div[5]/div/div/div/span/div/a/div")))
        return True
    except Exception:
        logging.info("Logged in indicator not found. User is not logged in.")
        return False

def initialize_browser():
    # Define custom user-agent string
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    
    # Define options for Chrome WebDriver
    options = webdriver.ChromeOptions()
    
    # Add the user-agent to the options
    options.add_argument(f"user-agent={user_agent}")
    
    # Use webdriver_manager to download and install the compatible ChromeDriver version
    chrome_driver_path = ChromeDriverManager().install()

    # Initialize the Service object with the executable path
    service = Service(executable_path=chrome_driver_path)

    # Initialize the browser
    driver = webdriver.Chrome(service=service)
    return driver

# Function to wait for successful login and redirection to home page
def wait_for_redirect(driver):
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable("/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[2]/div[5]/div/div/div/span/div/a/div"))

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    class JSVariableTruthy(object):
        def __init__(self, variable_name):
            self.variable_name = variable_name

        def __call__(self, driver):
            try:
                value = driver.execute_script(f"return {self.variable_name};")
                return value is not None and value != []
            except:
                return False
    
    # Initialize the browser
    browser = initialize_browser()
    browser.get("https://www.instagram.com/")

    # Check for existing cookies
    if load_cookies(browser):
        browser.get("https://www.instagram.com/")
        logging.info("Using existing cookies to open Instagram.")

        # Check if the user is logged in
        if is_logged_in(browser):
            logging.info("Logged in successfully.")
        else:
            logging.warning("Logged in with existing cookies but redirected to the login page. Please check if the cookies are valid.")
    else:
        logging.info("No existing cookies found. Please log in manually.")
        browser.get("https://www.instagram.com/")
        logging.info("Please log in manually.")

        # Wait for successful login and redirection to home page
        wait_for_redirect(browser)

        # Save session cookies
        save_cookies(browser)
        
        logging.info("Successfully logged in.")

    time.sleep(8)
    
    # Wait for the iframe to be available and switch to it
    iframe_selector = "/html/body/div[2]/div/div/div[3]/iframe"
    WebDriverWait(browser, 20).until(
        EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, iframe_selector)
        )
    )
    
    # Function to check if a username exists in the users table
    def username_exists(username):
        try:
            session.query(User).filter(User.username == username).one()
            return True
        except NoResultFound:
            return False

    # Function to check if a username exists in the sent_users table
    def is_username_sent(username):
        try:
            session.query(SentUser).filter(SentUser.username == username).one()
            return True
        except NoResultFound:
            return False

    # Function to add a username to the sent_users table
    def add_sent_username(username):
        sent_user = SentUser(username=username)
        session.add(sent_user)
        session.commit()
    
    # Prompt user to input the hashtag
    target_user = input("Enter the User you want to target: ")
    url = f"https://www.instagram.com/{target_user}"
    browser.get(url)
    logging.info("Scraping started from %s.", url)
    
    time.sleep(15)
    
    # JavaScript code to scrape followings
    javascript_code = """
    const username = arguments[0];
    let followings = [];

    (async () => {
        // Code to scrape followings
        const userQueryRes = await fetch(
        `https://www.instagram.com/web/search/topsearch/?query=${username}`
        );

        const userQueryJson = await userQueryRes.json();

        const userId = userQueryJson.users[0].user.pk;

        let after = null;
        let has_next = true;

        while (has_next) {
        await fetch(
            `https://www.instagram.com/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables=` +
            encodeURIComponent(
                JSON.stringify({
                id: userId,
                include_reel: true,
                fetch_mutual: true,
                first: 50,
                after: after,
                })
            )
        )
            .then((res) => res.json())
            .then((res) => {
            has_next = res.data.user.edge_follow.page_info.has_next_page;
            after = res.data.user.edge_follow.page_info.end_cursor;
            followings = followings.concat(
                res.data.user.edge_follow.edges.map(({ node }) => {
                return {
                    username: node.username,
                    full_name: node.full_name,
                };
                })
            );
            });
        }

        // Store followings in a globally accessible variable
        window.followings = followings;
    })();

    """

    # Execute JavaScript to scrape followings
    browser.execute_script(javascript_code, target_user)

    # Wait for the window.followings variable to be populated
    wait = WebDriverWait(browser, 120)  # Adjust the timeout as needed
    try:
        wait.until(JSVariableTruthy("window.followings"))

        # Retrieve the value of the variable containing the response
        response = browser.execute_script("return window.followings;")

        # Retrieve usernames from the sent_users table
        sent_usernames = {sent_user.username for sent_user in session.query(SentUser).all()}

        # Prepare a list to hold User objects to be added
        users_to_add = []

        # Iterate over the response to create User objects
        for following in response:
            username = following['username']
            if not username_exists(username) and username not in sent_usernames:
                # Create a User object and add it to the list
                user = User(username=username)
                users_to_add.append(user)
                print(f"Username added: {username}")

        # Add all User objects to the session
        if users_to_add:
            session.add_all(users_to_add)
            session.commit()

    except Exception as e:
        print("Error:", e)


    # Close the browser and session
    browser.quit()
    session.close()


if __name__ == "__main__":
    main()
