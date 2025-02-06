from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import undetected_chromedriver as uc
# from csgostash_scraper.modules.scraper import RetrieveCollection
# from csgostash_scraper.modules.objectfactory import CollectionFactory
import requests
import json
import os
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
    """Initialize Chrome driver with Steam authentication."""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)
    
    # First visit Steam
    print("Initializing Steam authentication...")
    driver.get("https://steamcommunity.com")
    time.sleep(2)
    
    # Add all necessary Steam cookies
    steam_cookies = [
        {
            'name': 'steamLoginSecure',
            'value': '76561198369694237||eyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxOV8yNUMzMEI2MF85RTg0MyIsICJzdWIiOiAiNzY1NjExOTgzNjk2OTQyMzciLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3Mzg5MTE5NDIsICJuYmYiOiAxNzMwMTg0NjUyLCAiaWF0IjogMTczODgyNDY1MiwgImp0aSI6ICIwMDBBXzI1Q0M0NTMwXzdBNjZEIiwgIm9hdCI6IDE3MzgxNzEyNTQsICJydF9leHAiOiAxNzU2NzQ1NTI2LCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTUyLjE1LjExMi43NyIsICJpcF9jb25maXJtZXIiOiAiMTcyLjU5LjIxNi4yMjMiIH0.uSClWebh3EQMkmSgbrtlB8OAmTwPq0gPFPz5t4Edcrb4WhF0J9rXdG4A0mOYQ2t-kAzMIZl7TcpxRWhwJHsACg',
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
    
    # Verify cookies and get price history
    print("Verifying Steam authentication...")
    driver.refresh()
    time.sleep(3)
    
    # Check if all cookies were set
    cookies = driver.get_cookies()
    cookie_names = [cookie['name'] for cookie in cookies]
    print("Current cookies:", cookie_names)
    
    return driver

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

def get_steam_price_history(market_hash_name):
    """Fetches price history from Steam Market."""
    driver = None
    try:
        driver = initialize_driver_steam_auth()
        
        # Visit the market listing page directly
        listing_url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}"
        print(f"\nVisiting listing page: {listing_url}")
        driver.get(listing_url)
        
        # Wait for page to load completely
        time.sleep(5)
        
        # First try to get price history from the API
        price_history_url = f"https://steamcommunity.com/market/pricehistory/?country=US&currency=1&appid=730&market_hash_name={quote(market_hash_name)}"
        print(f"Fetching price history from API: {price_history_url}")
        
        driver.get(price_history_url)
        time.sleep(3)
        
        try:
            raw_data = driver.find_element(By.TAG_NAME, "pre").text
            if raw_data and raw_data != '[]':
                data = json.loads(raw_data)
                if 'prices' in data:
                    print("Successfully retrieved price history from API")
                    return data['prices']
        except:
            print("Could not get price history from API, trying page JavaScript...")
            
            # If API fails, try getting it from the page
            driver.get(listing_url)
            time.sleep(5)
            
            try:
                price_history = driver.execute_script("return g_rgPriceHistory;")
                if price_history:
                    print("Successfully retrieved price history from page")
                    return price_history
            except Exception as e:
                print(f"Failed to get price history from page: {e}")
        
        print("Could not retrieve price history data")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None
    
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
            
    

