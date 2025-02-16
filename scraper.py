from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
import time
import undetected_chromedriver as uc
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import pyautogui
# from csgostash_scraper.modules.scraper import RetrieveCollection
# from csgostash_scraper.modules.objectfactory import CollectionFactory
import requests
import json
import os
import time
from urllib.parse import quote

API_KEY="Z6Y0JME93XWPCD7S"

# Define the URLs of the marketplaces to scrape
STEAM_URL = 'https://steamcommunity.com/market/search'
SKINPORT_URL = 'https://skinport.com/market?search='
STEAM_PRICE_HISTORY_URL = 'https://steamcommunity.com/market/pricehistory/'
DATABASE_FILE = 'csgo_skins_database.json'

# Define headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

# List of valid wear conditions with aliases
WEAR_CONDITIONS = {
    'fn': 'Factory New',
    'factory new': 'Factory New',
    'mw': 'Minimal Wear',
    'minimal wear': 'Minimal Wear',
    'ft': 'Field-Tested',
    'field-tested': 'Field-Tested',
    'ww': 'Well-Worn',
    'well-worn': 'Well-Worn',
    'bs': 'Battle-Scarred',
    'battle-scarred': 'Battle-Scarred',
    'all': 'all'
}


# Function to initialize the Chrome driver with undetected_chromedriver
def initialize_driver_basic():
    """Initialize basic undetected Chrome driver for Skinport and regular Steam market scraping."""
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = uc.Chrome(options=options)
    return driver

def initialize_driver_steam_auth():
    """Initialize Firefox driver with Steam authentication for price history."""
    options = webdriver.FirefoxOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Initialize Firefox driver with geckodriver
    driver = webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install()),
        options=options
    )
    
    print("Initializing Steam authentication...")
    driver.get("https://steamcommunity.com")
    time.sleep(2)
    
    # Add Steam cookies
    steam_cookies = [
        {
            'name': 'steamLoginSecure',
            'value': '76561198369694237%7C%7CeyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxMF8yNUQ2RUQ1OV9DNjM3NSIsICJzdWIiOiAiNzY1NjExOTgzNjk2OTQyMzciLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3Mzk3NTYxNDMsICJuYmYiOiAxNzMxMDI5NTI3LCAiaWF0IjogMTczOTY2OTUyNywgImp0aSI6ICIwMDBBXzI1RDZFQkUxX0JDMkZDIiwgIm9hdCI6IDE3Mzk2Njk1MjcsICJydF9leHAiOiAxNzU3ODQzOTc5LCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTczLjk1LjU3LjE5NSIsICJpcF9jb25maXJtZXIiOiAiMTczLjk1LjU3LjE5NSIgfQ.Rkjy94Kdvm6BZrmaybyZwRGPKFIZ__l68l5z7LC9ougBJjAV2zxApIvVhz-tkMDh-oiKc-ahFk7UlrCjF2FNCQ',
            'domain': '.steamcommunity.com',
            'path': '/'
        },
        {
            'name': 'sessionid',
            'value': '48d320d8ba8d66b88498e67f',
            'domain': '.steamcommunity.com',
            'path': '/'
        },
        {
            'name': 'browserid',
            'value': '257370855405343345',
            'domain': '.steamcommunity.com',
            'path': '/'
        }
    ]
    
    for cookie in steam_cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Failed to add cookie {cookie['name']}: {e}")
    
    driver.refresh()
    time.sleep(3)
    
    return driver

def initialize_driver_steam_auth_firefox():
    """Initialize Firefox driver with Steam authentication for price history."""
    try:
        options = webdriver.FirefoxOptions()
        driver = webdriver.Firefox(options=options)
        
        print("Initializing Steam authentication...")
        driver.get("https://steamcommunity.com")
        time.sleep(2)
        
        # Add Steam cookies
        steam_cookies = [
            {
                'name': 'steamLoginSecure',
                'value': '76561198369694237||eyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxOV8yNUMzMEI2MF85RTg0MyIsICJzdWIiOiAiNzY1NjExOTgzNjk2OTQyMzciLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3MzgyNTgzMTUsICJuYmYiOiAxNzI5NTMxMjU0LCAiaWF0IjogMTczODE3MTI1NCwgImp0aSI6ICIwMDBBXzI1QzMwQjYyX0IxMzkxIiwgIm9hdCI6IDE3MzgxNzEyNTQsICJydF9leHAiOiAxNzU2NzQ1NTI2LCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTUyLjE1LjExMi43NyIsICJpcF9jb25maXJtZXIiOiAiMTcyLjU5LjIxNi4yMjMiIH0.rWYVmbO8UnJ2zTiTXrJbtgAkVRmfgw7cPPJM-M-_C0DqNDp3t1Ar0-bm-7M0yXtzwJoCapxigSQsmLR4w2ahBw',
                'domain': '.steamcommunity.com',
                'path': '/'
            },
            {
                'name': 'sessionid',
                'value': 'c7a44057ae59052736d5adfa',
                'domain': '.steamcommunity.com',
                'path': '/'
            },
            {
                'name': 'browserid',
                'value': '115506104732364917',
                'domain': '.steamcommunity.com',
                'path': '/'
            }
        ]
        
        for cookie in steam_cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Failed to add cookie {cookie['name']}: {e}")
        
        driver.refresh()
        time.sleep(3)
        
        return driver
    except Exception as e:
        print(f"Error initializing Firefox driver: {e}")
        return None

def get_steam_price_history(market_hash_name):
    """Fetches price history from Steam Market and saves the data."""
    driver = None
    try:
        # Define save directory at the start of the function
        save_directory = "C:\\Users\\harsh\\GitHub\\cs-skin-price-tracker"
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        driver = initialize_driver_steam_auth()
        
        # Then construct and visit the price history URL
        price_history_url = "https://steamcommunity.com/market/pricehistory/"
        params = {
            'country': 'US',
            'currency': 1,
            'appid': 730,
            'market_hash_name': market_hash_name
        }
        
        query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        full_price_history_url = f"{price_history_url}?{query_string}"
        
        print(f"Fetching price history from: {full_price_history_url}")
        driver.get(full_price_history_url)
        
        # Wait for data to load
        time.sleep(2)
        
        print(f"Current URL: {driver.current_url}")
        
        
        try:
            save_button = driver.find_element(By.CSS_SELECTOR, "button.btn.save")
            save_button.click()
            print("Save dialog opened")
            
            # Wait for the save dialog to appear
            time.sleep(1)
            
            # Focus on address bar and paste the directory
            pyautogui.hotkey('alt', 'd')
            time.sleep(1)
            pyautogui.write(save_directory)
            pyautogui.press('enter')
            time.sleep(2)
            
            # Tab to filename field
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            
            # Clear any existing filename and type new one
            pyautogui.hotkey('ctrl', 'a')  # Select all
            time.sleep(0.5)
            safe_filename = f"{market_hash_name.replace('|', '-').replace('/', '-')}.json"
            pyautogui.write(safe_filename)
            time.sleep(1)
            pyautogui.press('tab')
            
            # Open dropdown and select "All Files"
            pyautogui.press('down')
            time.sleep(0.5)
            for _ in range(2):  # Press up multiple times to reach "All Files"
                pyautogui.press('down')
            
            # Save the file
            pyautogui.press('enter')
            pyautogui.press('enter')
            print(f"File saved as: {os.path.join(save_directory, safe_filename)}")
            
            # Wait for the save to complete
            time.sleep(3)
            
        except Exception as e:
            print(f"Couldn't handle save dialog: {e}")
            print(f"Detailed error: {str(e)}")
            
        # Get the data for processing
        try:
            pre_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            
            raw_data = pre_element.text
            data = json.loads(raw_data)
            
            if 'prices' in data:
                print("Successfully retrieved price history data")
                return data['prices']
            
        except Exception as e:
            print(f"Error getting price data: {e}")
        
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()

# Function to handle cookie popup
def handle_cookie_popup(driver):
    try:
        popup = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'CookiePopup'))
        )
        accept_button = popup.find_element(By.TAG_NAME, 'button')
        accept_button.click()
        time.sleep(2)
    except Exception:
        pass  # If no popup appears, continue normally
    

# Function to scrape skin prices from Steam
def scrape_steam_skin_prices(skin_name, wear_condition=None):
    driver = None
    try:
        driver = initialize_driver_basic()
        search_query = f"{skin_name} {wear_condition}" if wear_condition and wear_condition.lower() != 'all' else skin_name
        search_url = f"{STEAM_URL}?q={search_query.replace(' ', '+')}"
        driver.get(search_url)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        results = []
        for item in soup.find_all('div', class_='market_listing_row'):
            name_tag = item.find('span', class_='market_listing_item_name')
            price_tag = item.find('span', class_='normal_price')
            # Get the market_hash_name from the listing's data attributes
            market_hash_name = item.get('data-hash-name')
            
            if name_tag and price_tag and market_hash_name:
                results.append({
                    'name': name_tag.text.strip(),
                    'price': price_tag.text.strip(),
                    'market_hash_name': market_hash_name
                })
        
        return results
    
    except Exception as err:
        print(f"An error occurred: {err}")
        return []
    finally:
        if driver:
            driver.quit()
            


# Function to scrape the first 5 skin prices from Skinport with Cheapest First sorting
def scrape_skinport_skin_prices(skin_name, wear_condition=None):
    driver = None
    try:
        driver = initialize_driver_basic()
        
        conditions = ['Factory New', 'Minimal Wear', 'Field-Tested', 'Well-Worn', 'Battle-Scarred']
        results = []
        
        if wear_condition == 'all':
            for condition in conditions:
                search_query = f"{skin_name} {condition}".replace(' ', '+')
                search_url = f"https://skinport.com/market?search={search_query}&sort=price&order=asc"
                driver.get(search_url)
                print(f"Navigated to: {search_url}")
                
                handle_cookie_popup(driver)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'CatalogPage-items'))
                )
                print("Items grid loaded")
                
                time.sleep(3)  # Ensure dynamic content has fully loaded
                
                items = driver.find_elements(By.CSS_SELECTOR, '.CatalogPage-item')
                for item in items[:5]:
                    try:
                        name = item.find_element(By.CSS_SELECTOR, '.ItemPreview-itemName').text.strip()
                        price = item.find_element(By.CSS_SELECTOR, '.ItemPreview-priceValue .Tooltip-link').text.strip()
                        results.append({'name': name, 'price': price, 'condition': condition})
                    except Exception as e:
                        print(f"Failed to extract item details for condition {condition}: {e}")
        else:
            search_query = f"{skin_name} {wear_condition}".replace(' ', '+')
            search_url = f"https://skinport.com/market?search={search_query}&sort=price&order=asc"
            driver.get(search_url)
            print(f"Navigated to: {search_url}")
            
            handle_cookie_popup(driver)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'CatalogPage-items'))
            )
            
            time.sleep(3)
            items = driver.find_elements(By.CSS_SELECTOR, '.CatalogPage-item')
            for item in items[:5]:
                name = item.find_element(By.CSS_SELECTOR, '.ItemPreview-itemName').text.strip()
                price = item.find_element(By.CSS_SELECTOR, '.ItemPreview-priceValue .Tooltip-link').text.strip()
                results.append({'name': name, 'price': price, 'condition': wear_condition})
        
        return results
    except Exception as err:
        print(f"An error occurred: {err}")
        return []
    finally:
        if driver:
            driver.quit()

    
if __name__ == "__main__":
    skin_name = input("Enter the name of the skin: ").strip()
    wear_condition = input("Enter the wear condition (FN/MW/FT/WW/BS/All): ").strip().lower()
    wear_condition = WEAR_CONDITIONS.get(wear_condition, 'all')

    print("\n--- Steam Marketplace Results ---")
    steam_results = scrape_steam_skin_prices(skin_name, wear_condition)
    if steam_results:
        for idx, skin in enumerate(steam_results, start=1):
            print(f"{idx}. {skin['name']} - {skin['price']}")
            # Get price history for the first result
            if idx == 1:
                print("\n--- Steam Price History ---")
                price_history = get_steam_price_history(skin['market_hash_name'])
                if price_history:
                    print("Recent price history (last 5 entries):")
                    for date, price, quantity in price_history[-5:]:
                        print(f"{date}: ${price:.2f} ({quantity} sold)")
                else:
                    print("Could not fetch price history.")

    print("\n--- Skinport Marketplace Results ---")
    skinport_results = scrape_skinport_skin_prices(skin_name, wear_condition)
    if skinport_results:
        for idx, skin in enumerate(skinport_results, start=1):
            print(f"{idx}. {skin['name']} ({skin['condition']}) - {skin['price']}")
            
    

