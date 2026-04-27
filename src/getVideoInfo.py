from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time


#this function gets the game title from twitch UI
def get_game_title(video_id):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (no browser window)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Setup WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    #print("getting video data https://www.twitch.tv/videos/"+ video_id) 
    driver.get("https://www.twitch.tv/videos/"+ video_id)
    time.sleep(5)  # Wait for JavaScript to load

    try:
        # Find the anchor tag with the specific data-a-target
        game_link_element = driver.find_element(By.CSS_SELECTOR, 'a[data-a-target="video-info-game-boxart-link"]')
        
        # Find the <p> tag inside the anchor, ignoring the class name
        #game_name_element = game_link_element.find_element(By.TAG_NAME, "p")
        game_name_element = game_link_element.accessible_name
        
        # Extract the game name text
        #game_name = game_name_element.text.strip().replace(":","")
        game_name = game_name_element.strip().replace(":","")
        return game_name
    except:
        print("Game name not found.")
        return None
    finally:
        driver.quit()  # Close browser


# Example Usage:
#video_url = "https://www.twitch.tv/videos/2364549182"
#game_name = get_game_name_selenium(video_url)

#if game_name:
#    print(f"Game Name: {game_name}")