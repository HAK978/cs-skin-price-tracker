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
import psycopg2
from datetime import datetime

API_KEY="Z6Y0JME93XWPCD7S"

# Define the URLs of the marketplaces to scrape
STEAM_URL = 'https://steamcommunity.com/market/search?appid=730'
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


class DatabaseHandler:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="cs_skins",
                user="postgres",
                password="your_password_here",  # Your PostgreSQL password
                host="localhost",
                port="5432"
            )
            self.cur = self.conn.cursor()
            print("Successfully connected to database")
        except Exception as e:
            print(f"Database connection error: {e}")

    def load_json_to_db(self, json_file_path):
        """Load price history from JSON file into database"""
        try:
            # Read JSON file
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Get market_hash_name from filename
            market_hash_name = Path(json_file_path).stem.replace(' - ', ' | ')
            print(f"Processing data for: {market_hash_name}")

            # Insert skin into skins table
            self.cur.execute("""
                INSERT INTO skins (market_hash_name)
                VALUES (%s)
                ON CONFLICT (market_hash_name) DO NOTHING
                RETURNING skin_id
            """, (market_hash_name,))
            
            result = self.cur.fetchone()
            if result:
                skin_id = result[0]
                print(f"Created new skin with ID: {skin_id}")
            else:
                self.cur.execute("SELECT skin_id FROM skins WHERE market_hash_name = %s", 
                               (market_hash_name,))
                skin_id = self.cur.fetchone()[0]
                print(f"Found existing skin with ID: {skin_id}")

            # Process price history
            price_history_data = []
            currency = data['price_prefix']  # '₹' from your JSON

            for date_str, price, volume in data['prices']:
                try:
                    # Convert timestamp
                    date_str = date_str.replace(": +0", ":00 +0000")
                    timestamp = datetime.strptime(date_str, '%b %d %Y %H:%M %z')
                    
                    # Convert price to USD
                    price_usd = float(price) * 0.012  # Basic INR to USD conversion
                    
                    price_history_data.append((
                        timestamp,
                        skin_id,
                        price_usd,
                        float(price),  # Original price in INR
                        currency,
                        int(volume)
                    ))
                except Exception as e:
                    print(f"Error processing entry: {date_str}, {price}, {volume}")
                    print(f"Error details: {e}")

            # Batch insert price history
            self.cur.executemany("""
                INSERT INTO price_history 
                    (time, skin_id, price_usd, price_original, currency, volume)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, skin_id) DO UPDATE SET
                    price_usd = EXCLUDED.price_usd,
                    price_original = EXCLUDED.price_original,
                    volume = EXCLUDED.volume
            """, price_history_data)
            
            self.conn.commit()
            print(f"Successfully saved {len(price_history_data)} price entries to database")
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error processing file {json_file_path}: {e}")

    def close(self):
        self.cur.close()
        self.conn.close()
        print("Database connection closed")

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
            'value': '76561198369694237%7C%7CeyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAwQ18yNURFQkEyNF85MjkyRSIsICJzdWIiOiAiNzY1NjExOTgzNjk2OTQyMzciLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3NDA1MjY4NjYsICJuYmYiOiAxNzMxNzk5MzE3LCAiaWF0IjogMTc0MDQzOTMxNywgImp0aSI6ICIwMDBBXzI1REVCQTE4X0M0RTYwIiwgIm9hdCI6IDE3NDA0MzkzMTcsICJydF9leHAiOiAxNzU4ODI1MzMxLCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTUyLjE1LjExMi4yNTEiLCAiaXBfY29uZmlybWVyIjogIjE1Mi4xNS4xMTIuMjQ5IiB9.ppbqixD8MXaFnm04TAJj7GITIFFsZNDYqdZ4Z3gNPhGXqK15aFKIhUitshOES504hk5v2RrKYQ5p-5-XBih_AQ',
            'domain': '.steamcommunity.com',
            'path': '/'
        },
        {
            'name': 'sessionid',
            'value': 'b7f62df876c6ca0fa2e2b531',
            'domain': '.steamcommunity.com',
            'path': '/'
        },
        {
            'name': 'browserid',
            'value': '117759806768484693',
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
        time.sleep(1)
        
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
            time.sleep(1)
            
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
            time.sleep(1)
            
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
        search_url = f"{STEAM_URL}&q={search_query.replace(' ', '+')}"
        driver.get(search_url)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        print(f"Navigated to: {search_url}")
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
        elif wear_condition == 'none':
            search_query = f"{skin_name}".replace(' ', '+')
            search_url = f"https://skinport.com/market?search={search_query}&sort=price&order=asc"
            driver.get(search_url)
            print(f"Navigated to: {search_url}")
            
            handle_cookie_popup(driver)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'CatalogPage-items'))
            )
            print("Items grid loaded")
            name = item.find_element(By.CSS_SELECTOR, '.ItemPreview-itemName').text.strip()
            price = item.find_element(By.CSS_SELECTOR, '.ItemPreview-priceValue .Tooltip-link').text.strip()
            results.append({'name': name, 'price': price, 'condition': condition})
            time.sleep(3)
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
    wear_condition = input("Enter the wear condition (FN/MW/FT/WW/BS/All/None): ").strip().lower()
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
                    print(f"Got price history data with {len(price_history)} entries")
                    # Save to database
                    db = DatabaseHandler()
                    try:
                        db.save_price_history(skin['market_hash_name'], price_history)
                    except Exception as e:
                        print(f"Error in main while saving to database: {e}")
                    finally:
                        db.close()

                    # Display the data
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
    

