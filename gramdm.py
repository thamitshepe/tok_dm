import time
import random
import logging
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
from sqlalchemy import func  # Import func for random
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai
import textwrap
from IPython.display import Markdown
import dotenv
import os

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

def initialize_browser():
    
    # Define custom user-agent string
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    
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

# Function to wait for successful login and redirection to home page
def wait_for_redirect(driver):
    WebDriverWait(driver, 120).until(EC.element_to_be_clickable("/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[2]/div[5]/div/div/div/span/div/a/div"))

# Function to filter out non-BMP characters
def filter_non_bmp(text):
    return ''.join(char for char in text if ord(char) < 0x10000)

# Function to send keys with a random delay between each keystroke
def slow_send_keys(element, text, min_delay=0.0001, max_delay=0.0005):
    for char in text:
        element.send_keys(char)
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

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
            
            # Wait for the button to be clickable
            not_now_button = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button._a9--._ap36._a9_1"))
            )

            # Click the button
            not_now_button.click()
            
            time.sleep(random.uniform(2, 8))
            
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
        
        
    # Function to generate tailored outreach message using Gemini API
    def generate_outreach_message(display_name, bio, industry_role, post_descriptions):
        try:
            # Configure API key
            GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=GOOGLE_API_KEY)
            
            # Construct prompt for keyword extraction
            keyword_prompt = f"Extract any useful keywords and info and the persons name for creating an effective, no brainer outreach message from the display name, industry or role, bio and posts provided below, return in comma seperated list\n\n"
            keyword_prompt += f"Bio: {bio}\n"
            keyword_prompt += f"Industry/Role: {industry_role}\n"
            keyword_prompt += f"Display Name: {display_name}\n"
            keyword_prompt += f"Username: {user.username}\n"
            keyword_prompt += f"Post Descriptions:\n"
            for i, description in enumerate(post_descriptions, start=1):
                keyword_prompt += f"{i}. {description}\n"
            keyword_prompt += "\nKeywords:"

            # Call Gemini API for keyword extraction
            keyword_response = genai.GenerativeModel('gemini-pro').generate_content(keyword_prompt)

            # Extracting keywords from the response
            keywords = keyword_response.text.strip().split(',')

            # Constructing prompt for message generation
            prompt = f"Craft a neat tailored outreach message, You communicate a feeling and outcome more than just features or services, you connect with people, you understand their true nature and that its better to be clear and concise\n\n"
            prompt += f"Only utilize info from keywords in creating a tailored outreach message, it should make sense, only use this info, never include any special characters in the generated message eg #, *, [, +, etc\n"
            prompt += f"Refrain from anything that may seem untruthful, eg I've been following you, or I'm such a fan etc, keep it professional, always ensure the message makes sense, refrain from any placeholders\n"
            prompt += f"Outreach message is for services around tailored software solutions, ai integration and automation for my business at Thami.ai, dont mention the business though, focus on them\n"
            prompt += f"Keywords: {', '.join(keywords)}"
            prompt += f"closely follow this message structure:\n"
            prompt += f"- Warm and short greeting with the prospect's name from {display_name} or possibly from other info provided, if display name not present use @{user.username} instead,\n"
            prompt += f"- 1 sentence referencing their work or background. Using keywords, don't make anything up, if keywords insufficient keep it friendly, something like looking to explore potential synergies\n"
            prompt += f"- 1 descriptive sentence on how you can help optimize or elevate their business operations starting with 'I'd be glad to assist with...', leading to a call to action like 'Let me know if you'd like to reclaim what matters most'\n"

            # Call Gemini API for message generation
            message_response = genai.GenerativeModel('gemini-pro').generate_content(prompt)

            # Parsing and returning the generated message
            generated_message = message_response.text.strip()
            return generated_message
        
        except ValueError as ve:
            logging.error("Error extracting keywords: %s", ve)
            return None
        except Exception as e:
            logging.error("Error generating outreach message: %s", e)
            return None

    # Modify this query to randomize the order of users fetched
    # Adjust `func.random()` if your database uses a different function for random sorting
    users = session.query(User).order_by(func.random()).limit(50).all()

    for user in users:
        if session.query(SentUser).filter_by(username=user.username).first():
            logging.info(f"User {user.username} already exists in the sent_users table. Skipping.")
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            logging.info(f"User {user.username} deleted from users table.")
            continue

        profile_url = f"https://www.instagram.com/{user.username}"
        browser.get(profile_url)
        logging.info(f"Visiting profile page of user: {user.username}")

        javascript_code = """
        const username = arguments[0];
        (async () => {
            const userQueryRes = await fetch(`https://www.instagram.com/web/search/topsearch/?query=${username}`);
            const userQueryJson = await userQueryRes.json();
            const isPrivate = userQueryJson.users[0].user.is_private;
            window.private = isPrivate; // Store private value in a globally accessible variable
        })();
        """
        browser.execute_script(javascript_code, user.username)

        # Check for window.private to be populated
        wait = WebDriverWait(browser, 120)  # Adjust timeout as needed
        try:
            wait.until(JSVariableTruthy("window.private"))
            is_private = browser.execute_script("return window.private;")
            
            if is_private:
                logging.info(f"User {user.username}'s profile is private. Deleting and skipping.")
                session.query(User).filter_by(username=user.username).delete()
                session.commit()
                continue
        except Exception as e:
            logging.error(f"Error checking if profile is private for user {user.username}: {e}")
            continue
        

        # Extracting the text
        try:
            display_name_element = WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0vuye.xvs91rp.x1s688f.x5n08af.x10wh9bi.x1wdrske.x8viiok.x18hxmgj"))
            )
            display_name = display_name_element.text
        except TimeoutException:
            display_name = "Display name not present"

        try:
            industry_role_element = WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div._ap3a._aaco._aacu._aacy._aad6._aade"))
            )
            industry_role = industry_role_element.text
        except TimeoutException:
            industry_role = "Industry role not present"

        try:
            bio_element = WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad6._aade"))
            )
            bio = bio_element.text
        except TimeoutException:
            bio = "Bio not present"


        # Check if the post container exists, if not, return "No post descriptions present"
        try:
            post_container = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/div[3]/div/div[1]/div[1]/a"))
            )
            
            # Click on the post container
            post_container.click()

            # Wait for a random time
            time.sleep(random.uniform(2, 8))

            # Click the like button
            like_button_selector = "body > div.x1n2onr6.xzkaem6 > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div > div.xb88tzc.xw2csxc.x1odjw0f.x5fp0pe.x1qjc9v5.xjbqb8w.x1lcm9me.x1yr5g0i.xrt01vj.x10y3i5r.xr1yuqi.xkrivgy.x4ii5y1.x1gryazu.x15h9jz8.x47corl.xh8yej3.xir0mxb.x1juhsu6 > div > article > div > div.x1qjc9v5.x972fbf.xcfux6l.x1qhh985.xm0m39n.x9f619.x78zum5.xdt5ytf.x1iyjqo2.x5wqa0o.xln7xf2.xk390pu.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.x65f84u.x1vq45kp.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1n2onr6.x11njtxf > div > div > div.x78zum5.xdt5ytf.x1q2y9iw.x1n2onr6.xh8yej3.x9f619.x1iyjqo2.x18l3tf1.x26u7qi.xy80clv.xexx8yu.x4uap5.x18d9i69.xkhd6sd > section.x78zum5.x1q0g3np.xwib8y2.x1yrsyyn.x1xp8e9x.x13fuv20.x178xt8z.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xo1ph6p.x1pi30zi.x1swvt13 > span.x1rg5ohu.xp7jhwk > div"
            like_button = browser.find_element(By.CSS_SELECTOR, like_button_selector)
            browser.execute_script("arguments[0].click();", like_button)

            try:
                # Extract text from the first post description
                first_post_description = browser.find_element(By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad7._aade").text

                # Initialize a list to store post descriptions
                post_descriptions = [first_post_description]
            except NoSuchElementException:
                first_post_description = "First post description not present"
                post_descriptions = [first_post_description]
            
            # Check if the next button is present
            for i in range(3):
                try:
                    time.sleep(4)
                    next_button_xpath = "div._aaqg._aaqh > button"
                    next_button = browser.find_element(By.CSS_SELECTOR, next_button_xpath)
                    browser.execute_script("arguments[0].click();", next_button)
                    time.sleep(random.uniform(1, 4))  # Random wait between clicks
                    try:
                        post_description = browser.find_element(By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad7._aade").text
                        post_descriptions.append(post_description)
                    except NoSuchElementException:
                        post_description = "Description not present"
                        
                    # Randomly decide whether to click like or not
                    if random.choice([True, False]):
                        # Click the like button
                        like_button_selector = "body > div.x1n2onr6.xzkaem6 > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div > div.xb88tzc.xw2csxc.x1odjw0f.x5fp0pe.x1qjc9v5.xjbqb8w.x1lcm9me.x1yr5g0i.xrt01vj.x10y3i5r.xr1yuqi.xkrivgy.x4ii5y1.x1gryazu.x15h9jz8.x47corl.xh8yej3.xir0mxb.x1juhsu6 > div > article > div > div.x1qjc9v5.x972fbf.xcfux6l.x1qhh985.xm0m39n.x9f619.x78zum5.xdt5ytf.x1iyjqo2.x5wqa0o.xln7xf2.xk390pu.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.x65f84u.x1vq45kp.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1n2onr6.x11njtxf > div > div > div.x78zum5.xdt5ytf.x1q2y9iw.x1n2onr6.xh8yej3.x9f619.x1iyjqo2.x18l3tf1.x26u7qi.xy80clv.xexx8yu.x4uap5.x18d9i69.xkhd6sd > section.x78zum5.x1q0g3np.xwib8y2.x1yrsyyn.x1xp8e9x.x13fuv20.x178xt8z.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xo1ph6p.x1pi30zi.x1swvt13 > span.x1rg5ohu.xp7jhwk > div"
                        like_button = browser.find_element(By.CSS_SELECTOR, like_button_selector)
                        browser.execute_script("arguments[0].click();", like_button)
                    
                except NoSuchElementException:
                    # If next button is not present, break the loop
                    break
        except TimeoutException:
            # If post container is not found, set post_descriptions to "No post descriptions present"
            post_descriptions = "No post descriptions present"    

        print(display_name)
        print(industry_role)
        print(bio)
        print(post_descriptions)
        
        time.sleep(random.uniform(2, 8))

        # Generate a random sleep time between 10 and 25 seconds
        random_sleep = random.uniform(8, 35)

        # Generate tailored outreach message
        outreach_message = generate_outreach_message(display_name, industry_role, bio, post_descriptions)
        
        # Check if the outreach message was generated successfully
        if outreach_message is None:
            logging.error("Skipping user %s due to error in generating outreach message.", user.username)
            
            # Delete the user from the users table
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            
            logging.info("User %s deleted from users table.", user.username)
            
            continue
        
        logging.info("Generated message for user: %s", user.username)
        logging.info("Outreach Message: %s", outreach_message)
        
        # Generate the URL for the messages page
        messages_url = f"https://www.instagram.com/m/{user.username}"

        # Navigate to the messages page
        browser.get(messages_url)
        logging.info(f"Visiting messages page for user: {user.username}")

        # Wait for the iframe to be present
        try:
            iframe = WebDriverWait(browser, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='fr']"))
            )
            # Switch to the iframe
            browser.switch_to.frame(iframe)
            logging.info("Switched to messages iframe.")

            # Check if the second element is present
            second_element_present = False
            try:
                second_element = browser.find_element(By.CSS_SELECTOR, "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0vuye.xvs91rp.xo1l8bm.x1roi4f4.x2b8uid.x1tu3fi.x3x7a5m.x10wh9bi.x1wdrske.x8viiok.x18hxmgj")
                second_element_present = True
            except NoSuchElementException:
                pass

            if not second_element_present:
                # Reload the page and check again
                browser.refresh()
                time.sleep(random_sleep)

                # Check if the second element is present after reloading
                try:
                    second_element = browser.find_element(By.CSS_SELECTOR, "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0vuye.xvs91rp.xo1l8bm.x1roi4f4.x2b8uid.x1tu3fi.x3x7a5m.x10wh9bi.x1wdrske.x8viiok.x18hxmgj")
                    second_element_present = True
                except NoSuchElementException:
                    pass

                if not second_element_present:
                    # If second element is still not present, skip and delete user
                    logging.warning(f"Second element not found for user: {user.username}. Skipping and deleting.")
                    
                    # Delete user from users table
                    session.query(User).filter_by(username=user.username).delete()
                    session.commit()
                    logging.info(f"User {user.username} deleted from users table.")
                    
                    continue
        except TimeoutException:
            logging.error("Timeout waiting for the iframe to be present.")
            # Handle the exception or log the error as needed
            
        # Check if the input area is present
        input_area_present = False
        try:
            input_area = WebDriverWait(browser, 45).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Message"]')))
            input_area_present = True
        except TimeoutException:
            pass

        if not input_area_present:
            # Reload the page and check again
            browser.refresh()
            time.sleep(random_sleep)

            # Check if the input area is present after reloading
            try:
                input_area = WebDriverWait(browser, 45).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Message"]')))
                input_area_present = True
            except TimeoutException:
                pass

            if not input_area_present:
                # If input area is still not present, skip and delete user
                logging.warning(f"Input area not found for user: {user.username}. Skipping and deleting.")
                
                # Delete user from users table
                session.query(User).filter_by(username=user.username).delete()
                session.commit()
                logging.info(f"User {user.username} deleted from users table.")
                
                continue
            
            
        # Check if message sent indicator is present
        message_sent_indicator_present = False
        try:
            message_sent_indicator = browser.find_element(By.CSS_SELECTOR, 'div.x1tlxs6b.x1g8br2z.x1gn5b1j.x230xth.x14ctfv.x1okitfd.x6ikm8r.x10wlt62.x1mzt3pk.x1y1aw1k.xn6708d.xwib8y2.x1ye3gou.x1n2onr6.x13faqbe.x1vjfegm')
            message_sent_indicator_present = True
        except NoSuchElementException:
            pass

        if message_sent_indicator_present:
            # If message sent before, add user to sent_users table and delete from users table
            logging.info(f"Message previously sent for user: {user.username}.")
            
            # Add user to sent_users table (pseudo code, replace with actual SQL query)
            session.add(SentUser(username=user.username))
            session.commit()
            logging.info(f"User {user.username} added to sent_users table.")
            
            # Delete user from users table
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            logging.info(f"User {user.username} deleted from users table.")
            
            continue
        else:
            logging.info(f"No message sent previously for user: {user.username}. Proceeding to send message.")

        # Click on the input area to focus it
        input_area.click()

        # Replace line breaks with spaces in the outreach message
        outreach_message = outreach_message.replace('\n', ' ')
        message = filter_non_bmp(outreach_message)

        # Use the slow_send_keys function to send the filtered outreach message
        slow_send_keys(input_area, message)
        
        time.sleep(random.uniform(2, 8))

        # Find the send button
        send_button_selector = 'div.x1i10hfl.xjqpnuy.xa49m3k.xqeqjp1.x2hbi6w.xdl72j9.x2lah0s.xe8uvvx.xdj266r.xat24cr.x1mh8g0r.x2lwn1j.xeuugli.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1lku1pv.x1a2a7pz.x6s0dn4.xjyslct.x1ejq31n.xd10rxx.x1sy0etr.x17r0tee.x9f619.x1ypdohk.x1f6kntn.xwhw2v2.xl56j7k.x17ydfre.x2b8uid.xlyipyv.x87ps6o.x14atkfc.xcdnw81.x1i0vuye.xjbqb8w.xm3z3ea.x1x8b98j.x131883w.x16mih1h.x972fbf.xcfux6l.x1qhh985.xm0m39n.xt0psk2.xt7dq6l.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1n2onr6.x1n5bzlp.x173jzuc.x1yc6y37.xfs2ol5'
        send_button_present = False
        try:
            send_button = WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, send_button_selector)))
            send_button_present = True
        except TimeoutException:
            logging.warning("Send button did not show up within the specified time. Proceeding without sending the message.")
            continue
        
        if send_button_present:
            # Click on the send button to send the message
            send_button.click()

            # Add the user to the sent_users table
            sent_user = SentUser(username=user.username)
            session.add(sent_user)
            session.commit()
            logging.info("User %s added to sent_users table.", user.username)

            # Delete the user from the users table
            session.query(User).filter_by(username=user.username).delete()
            session.commit()
            logging.info("User %s deleted from users table.", user.username)
            
            time.sleep(random.uniform(16, 26))

        else:
            logging.warning("Send button was not present. Proceeding without sending the message.")
            continue

# End of the loop

    
    # Close the browser and session
    browser.quit()
    session.close()

if __name__ == "__main__":
    main()