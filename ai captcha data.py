import os
import random
import time
import numpy as np
import re
import cv2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Use webdriver_manager to download and install the compatible ChromeDriver version
chrome_driver_path = ChromeDriverManager().install()

# Initialize the Service object with the executable path
service = Service(executable_path=chrome_driver_path)

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--window-size=800,700")  # Set the desired window size

# Initialize the browser with the specified options
driver = webdriver.Chrome(service=service, options=chrome_options)

# Navigate to the TikTok login page
driver.get("https://www.tiktok.com/login/phone-or-email/email")

# Fill in the username and password
username_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-q83gm2-DivInputContainer.etcs7ny0 > input"))
)
username_field.send_keys(os.getenv("TIKTOK_USERNAME"))

password_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-15iauzg-DivContainer.e1bi0g3c0 > div > input"))
)
password_field.send_keys(os.getenv("TIKTOK_PASSWORD"))

# Click the login button
login_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > button"))
)
login_button.click()

# Wait for the captcha to show up
captcha = WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "#captcha_container"))
)

# Define the number of captcha challenges to capture
num_challenges = 10000

# Define the number of sliding steps and the maximum offset for each step
num_steps = 35
max_offset = 40
min_offset = -20

# Define the directory to save the images
image_dir = "slider_images"
os.makedirs(image_dir, exist_ok=True)

# Define the selectors
refresh_button_selector = "#captcha_container > div > div.captcha_verify_action.sc-jAaTju.jvNEQE > div > a.secsdk_captcha_refresh.refresh-button___StyledA-sc-18f114n-0.jgMJRc"
slider_selector = "#secsdk-captcha-drag-wrapper > div.secsdk-captcha-drag-icon.sc-kEYyzF.fiQtnm"

# Function to automatically detect inner circle position
def detect_inner_circle_position(image_path):
    # Load the captcha container image
    captcha_image = cv2.imread(image_path)

    # Convert the image to grayscale
    gray_image = cv2.cvtColor(captcha_image, cv2.COLOR_BGR2GRAY)

    # Enhance contrast
    enhanced_image = cv2.equalizeHist(gray_image)

    # Apply Gaussian blur to reduce noise
    blurred_image = cv2.GaussianBlur(enhanced_image, (5, 5), 0)

    # Thresholding to isolate bright areas (potential inner circle)
    _, binary_image = cv2.threshold(blurred_image, 200, 255, cv2.THRESH_BINARY)

    # Find contours in the binary image
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Iterate through contours and find the one representing the inner circle
    inner_circle_position = None
    max_contour_area = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_contour_area:
            max_contour_area = area
            # Get the bounding rectangle for the contour
            x, y, w, h = cv2.boundingRect(contour)
            # Assuming the inner circle is the smallest contour with a certain aspect ratio
            if w / h < 1.2:  # Adjust aspect ratio threshold as needed
                inner_circle_position = x + w // 2  # Return x-coordinate of center of bounding rectangle

    return inner_circle_position

# Initialize training data list
training_data = []

# Check existing files in the directory
existing_files = os.listdir(image_dir)

# Initialize variables to track the last completed challenge and step
last_completed_challenge = 0
last_completed_step = 0

# Parse existing filenames to find the highest challenge and step numbers
for filename in existing_files:
    match = re.match(r"slider_challenge_(\d+)_step_(\d+)", filename)
    if match:
        challenge_num = int(match.group(1))
        step_num = int(match.group(2))
        if challenge_num > last_completed_challenge:
            last_completed_challenge = challenge_num
            last_completed_step = step_num
        elif challenge_num == last_completed_challenge and step_num > last_completed_step:
            last_completed_step = step_num

# Determine the starting point for the scraping process
if last_completed_step < num_steps:
    # If the last completed step is less than the total steps, start from the beginning of the challenge
    start_challenge = last_completed_challenge
    start_step = 0
    
    # Remove files related to the incomplete challenge
    incomplete_challenge_files = [filename for filename in existing_files if f"slider_challenge_{last_completed_challenge}_" in filename]
    for filename in incomplete_challenge_files:
        os.remove(os.path.join(image_dir, filename))
else:
    # If the last completed step is the last step, start from the next challenge
    start_challenge = last_completed_challenge + 1
    start_step = 0

# Continue from the next challenge
for challenge in range(start_challenge, num_challenges + 1):
    # Wait for the refresh button to be clickable
    refresh_button = WebDriverWait(captcha, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, refresh_button_selector))
    )
    refresh_button.click()

    time.sleep(5)

    # Wait for the slider to be present
    slider = WebDriverWait(captcha, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, slider_selector))
    )

    # Take screenshot of the entire captcha container
    screenshot_path = os.path.join(image_dir, f"captcha_challenge_{challenge}.png")
    driver.save_screenshot(screenshot_path)

    # Save image of the captcha container
    captcha_element = driver.find_element(By.CSS_SELECTOR, "#captcha_container")
    location = captcha_element.location
    size = captcha_element.size
    left = location['x']
    top = location['y']
    right = location['x'] + size['width']
    bottom = location['y'] + size['height']
    full_image = cv2.imread(screenshot_path)
    captcha_container_cropped = full_image[top:bottom, left:right]
    cv2.imwrite(os.path.join(image_dir, f"captcha_container_{challenge}.png"), captcha_container_cropped)

    # Automatically detect inner circle position
    slider_image_path = os.path.join(image_dir, f"captcha_container_{challenge}.png")
    inner_circle_position = detect_inner_circle_position(slider_image_path)
    print(f"Challenge {challenge}: Inner circle position - {inner_circle_position}")

    # Perform sliding action
    if inner_circle_position is not None:
        # Perform click and drag action
        action = ActionChains(driver)
        action.click_and_hold(slider).perform()

        try:
            # Perform sliding action from the correct step
            for step in range(start_step, num_steps):
                # Calculate random offset for sliding
                sliding_offset = random.randint(min_offset, max_offset)
                print(f"Sliding offset: {sliding_offset}")

                # Perform sliding action
                action.move_by_offset(sliding_offset, 0).perform()

                time.sleep(0.5)  # Add a short delay for the slider animation

                # Take screenshot of the slider after sliding
                screenshot_path = os.path.join(image_dir, f"slider_challenge_{challenge}_step_{step + 1}_sliding_offset_{sliding_offset}_inner_circle_position_{inner_circle_position}.png")
                driver.save_screenshot(screenshot_path)

                # Automatically detect inner circle position after sliding
                inner_circle_position = detect_inner_circle_position(screenshot_path)
                print(f"Challenge {challenge}, Step {step + 1}: Inner circle position - {inner_circle_position}")

                # Save training data (image and target position)
                training_data.append((screenshot_path, inner_circle_position))

        except Exception as e:
            print(f"Error occurred during sliding: {e}")
            # Log the error and continue with the next challenge
            continue

    # Release the click after sliding is done
    action.release().perform()
    
    time.sleep(5)

    # Check if the browser URL changes to indicate successful login
    if driver.current_url == "https://www.tiktok.com/foryou?lang=en":
        # Append "_correct" to the filenames of screenshots if the challenge is correct
        for step in range(start_step, num_steps):
            screenshot_path = os.path.join(image_dir, f"slider_challenge_{challenge}_step_{step + 1}_sliding_offset_{sliding_offset}_inner_circle_position_{inner_circle_position}.png")
            screenshot_path_correct = screenshot_path[:-4] + "_correct.png"
            os.rename(screenshot_path, screenshot_path_correct)

# Close the browser
driver.quit()
