import time
import random
import logging
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai
import textwrap
from IPython.display import Markdown
import dotenv
import os

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

def initialize_browser():
    # Use webdriver_manager to download and install the compatible ChromeDriver version
    chrome_driver_path = ChromeDriverManager().install()

    # Initialize the Service object with the executable path
    service = Service(executable_path=chrome_driver_path)

    # Initialize the browser
    driver = webdriver.Chrome(service=service)
    return driver

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

# Function to wait for successful login and redirection to home page
def wait_for_redirect(driver):
    WebDriverWait(driver, 120).until(EC.url_contains("https://www.tiktok.com/foryou?lang=en"))

# Function to filter out non-BMP characters
def filter_non_bmp(text):
    return ''.join(char for char in text if ord(char) < 0x10000)

# Function to send keys with a random delay between each keystroke
def slow_send_keys(element, text, min_delay=0.02, max_delay=0.2):
    for char in text:
        element.send_keys(char)
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

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
        
    # Function to generate tailored outreach message using Gemini API
    def generate_outreach_message(display_name, bio, post_descriptions):
        # Configure API key
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Construct prompt for keyword extraction
        keyword_prompt = f"Extract any useful keywords and info and the person's name for creating an effective, no brainer outreach message from the display name, bio, and posts provided below, return in comma-separated list\n\n"
        keyword_prompt += f"Bio: {bio}\n"
        keyword_prompt += f"Display Name: {display_name}\n"
        keyword_prompt += f"Post Descriptions:\n"
        for i, description in enumerate(post_descriptions, start=1):
            keyword_prompt += f"{i}. {description}\n"
        keyword_prompt += "\nKeywords:"

        # Call Gemini API for keyword extraction
        keyword_response = genai.GenerativeModel('gemini-pro').generate_content(keyword_prompt)

        # Extracting keywords from the response
        keywords = keyword_response.text.strip().split(',')

        # Constructing prompt for message generation
        prompt = f"You are a mastersalesperson who crafts neat tailored outreach messages, You communicate a feeling and outcome more than just features or services, you connect with people, you understand their true nature and that its better to be clear and concise\n\n"
        prompt += f"Only utilize info below in creating a tailored outreach message, it should make sense, only use this info, you specialize in tailored software solutions, AI, and automation\n"
        prompt += f"Refrain from anything that may seem untruthful, eg I've been following you, or I'm such a fan etc, keep it professional, always ensure the message makes sense\n"
        prompt += f"Keywords: {', '.join(keywords)}"
        prompt += f"closely follow this message structure:\n"
        prompt += f"- Warm and short greeting with the prospect's name: Hi {display_name} or name,\n"
        prompt += f"- 1 sentence referencing their work or background.\n"
        prompt += f"- 1 descriptive sentence on how you can help optimize or elevate their business operations starting with 'I'd be glad to assist with...'\n"
        prompt += f"- Call to action: 'Let me know if you'd like to reclaim what matters most'\n\n"

        # Call Gemini API for message generation
        message_response = genai.GenerativeModel('gemini-pro').generate_content(prompt)

        # Parsing and returning the generated message
        generated_message = message_response.text.strip()
        return generated_message

    # Limit the number of users to process to 25
    users = session.query(User).limit(25).all()

    # Iterate through each user
    for user in users:
        # Check if the user has already been sent a message
        if session.query(SentUser).filter_by(username=user.username).first():
            logging.info("User %s already exists in the sent_users table. Skipping.", user.username)
            
            # Delete the user from the users table
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            
            logging.info("User %s deleted from users table.", user.username)
            
            continue

        # Construct the user's profile URL
        profile_url = f"https://www.tiktok.com/@{user.username}"

        # Visit the user's profile page
        browser.get(profile_url)
        logging.info("Visiting profile page of user: %s", user.username)

        # Wait for the bio, display name, and posts to load
        WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#main-content-others_homepage > div > div.css-1g04lal-DivShareLayoutHeader-StyledDivShareLayoutHeaderV2.enm41492 > h2")))
        WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#main-content-others_homepage > div > div.css-1g04lal-DivShareLayoutHeader-StyledDivShareLayoutHeaderV2.enm41492 > div.css-1gk89rh-DivShareInfo.ekmpd5l2 > div.css-1nbnul7-DivShareTitleContainer.ekmpd5l3 > h2")))
        WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".css-16ou6xi-DivTagCardDesc.eih2qak1")))

        # Extract and print user's bio and display name
        bio = browser.find_element(By.CSS_SELECTOR, "#main-content-others_homepage > div > div.css-1g04lal-DivShareLayoutHeader-StyledDivShareLayoutHeaderV2.enm41492 > h2").text.strip()
        display_name = browser.find_element(By.CSS_SELECTOR, "#main-content-others_homepage > div > div.css-1g04lal-DivShareLayoutHeader-StyledDivShareLayoutHeaderV2.enm41492 > div.css-1gk89rh-DivShareInfo.ekmpd5l2 > div.css-1nbnul7-DivShareTitleContainer.ekmpd5l3 > h2").text.strip()
      
        # Find all elements with the specified class
        post_descriptions_elements = browser.find_elements(By.CSS_SELECTOR, ".css-16ou6xi-DivTagCardDesc.eih2qak1")

        # Extract text from aria-label attribute of each element
        post_descriptions = [element.get_attribute("aria-label") for element in post_descriptions_elements]

        # Log the post descriptions
        for i, description in enumerate(post_descriptions[:5]):
            logging.info("Post %d Description: %s", i+1, description)
        
        # Limit post descriptions to 8 or less
        post_descriptions = post_descriptions[:8]

        # Generate tailored outreach message
        outreach_message = generate_outreach_message(display_name, bio, post_descriptions)
        logging.info("Generated message for user: %s", user.username)
        logging.info("Outreach Message: %s", outreach_message)
        
        # Find the message URL
        message_url_element = browser.find_element(By.CSS_SELECTOR, "#main-content-others_homepage > div > div.css-1g04lal-DivShareLayoutHeader-StyledDivShareLayoutHeaderV2.enm41492 > div.css-1gk89rh-DivShareInfo.ekmpd5l2 > div.css-1nbnul7-DivShareTitleContainer.ekmpd5l3 > div > div.css-b8igea-DivMessageContainer.e18e4obn1 > a")
        message_url = message_url_element.get_attribute("href")
        
        # Navigate to the message URL
        browser.get(message_url)
        logging.info("Navigating to message URL for user: %s", user.username)

        time.sleep(5)
        
        # Wait for the iframe to be available and switch to it
        iframe_selector = "#root > div.pb-2.w-full.flex.flex-col.overflow-hidden > div.pt-4.h-full.m-auto.flex.flex-1.relative.contact-card-container > div > div > iframe"
        WebDriverWait(browser, 35).until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, iframe_selector)))

        
        # Generate a random sleep time between 10 and 25 seconds
        random_sleep_time = random.uniform(10, 35)

        # Wait for the input area to be available
        try:
            input_area_selector = 'div[aria-label="Send a message..."]'
            input_area = WebDriverWait(browser, 35).until(EC.element_to_be_clickable((By.CSS_SELECTOR, input_area_selector)))

            # Click on the input area to focus it
            input_area.click()

            # Replace line breaks with spaces in the outreach message
            outreach_message = outreach_message.replace('\n', ' ')

            message = filter_non_bmp(outreach_message)

           # Use the slow_send_keys function to send the filtered outreach message
            slow_send_keys(input_area, message)
            
            
            # Find the element to click on after typing the message
            send_button_selector = '#main-content-messages > div.css-d0yksp-DivChatBox.ediam1h0 > div.css-fqfkc9-DivChatBottom.e1823izs0 > svg'

            send_button = WebDriverWait(browser, 35).until(EC.element_to_be_clickable((By.CSS_SELECTOR, send_button_selector)))
            
            time.sleep(random_sleep_time)
            
            # Click on the specified element
            send_button.click()
            
            time.sleep(random_sleep_time)

            # Switch back to the default content
            browser.switch_to.default_content()

            # Add the user to the sent_users table
            sent_user = SentUser(username=user.username)
            session.add(sent_user)
            session.commit()
            logging.info("User %s added to sent_users table.", user.username)

            # Delete the user from the users table
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            
            logging.info("User %s deleted from users table.", user.username)

        except TimeoutException:
            logging.warning("Input area did not show up within the specified time. Reloading the page.")
            
            # Reload the page
            browser.refresh()
            
            # Wait for the page to load after refreshing
            WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            
            # Check if the input area is available after reloading
            try:
                input_area = WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, input_area_selector)))

                # Click on the input area to focus it
                input_area.click()

                # Replace line breaks with spaces in the outreach message
                outreach_message = outreach_message.replace('\n', ' ')

                message = filter_non_bmp(outreach_message)

                # Use the slow_send_keys function to send the filtered outreach message
                slow_send_keys(input_area, message)
                
                # Find the element to click on after typing the message
                send_button_selector = '#main-content-messages > div.css-d0yksp-DivChatBox.ediam1h0 > div.css-fqfkc9-DivChatBottom.e1823izs0 > svg'

                send_button = WebDriverWait(browser, 35).until(EC.element_to_be_clickable((By.CSS_SELECTOR, send_button_selector)))
                
                time.sleep(random_sleep_time)
                
                # Click on the specified element
                send_button.click()
                
                time.sleep(random_sleep_time)

                # Switch back to the default content
                browser.switch_to.default_content()

                # Add the user to the sent_users table
                sent_user = SentUser(username=user.username)
                session.add(sent_user)
                session.commit()
                logging.info("User %s added to sent_users table.", user.username)

                # Delete the user from the users table
                session.query(User).filter_by(username=user.username).delete()
                session.commit()
                
                logging.info("User %s deleted from users table.", user.username)
                
            except TimeoutException:
                logging.error("Input area did not show up after reloading. Removing user %s from the users table.", user.username)
                
                # Remove the user from the users table
                session.query(User).filter_by(username=user.username).delete()
                session.commit()
                
                logging.info("User %s removed from users table.", user.username)
                
                time.sleep(random_sleep_time)
                
                continue
            
            
    # Close the browser and session
    browser.quit()
    session.close()

if __name__ == "__main__":
    main()