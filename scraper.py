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
def initialize_driver():
    """Initialize Chrome driver with Steam authentication."""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    
    # First visit Steam to set the cookie
    driver.get("https://steamcommunity.com")
    
    # Add the Steam authentication cookie
    steam_cookie = {
        'name': 'steamLoginSecure',
        'value': '76561198369694237||eyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxOV8yNUMzMEI2MF85RTg0MyIsICJzdWIiOiAiNzY1NjExOTgzNjk2OTQyMzciLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3MzgyNTgzMTUsICJuYmYiOiAxNzI5NTMxMjU0LCAiaWF0IjogMTczODE3MTI1NCwgImp0aSI6ICIwMDBBXzI1QzMwQjYyX0IxMzkxIiwgIm9hdCI6IDE3MzgxNzEyNTQsICJydF9leHAiOiAxNzU2NzQ1NTI2LCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTUyLjE1LjExMi43NyIsICJpcF9jb25maXJtZXIiOiAiMTcyLjU5LjIxNi4yMjMiIH0.rWYVmbO8UnJ2zTiTXrJbtgAkVRmfgw7cPPJM-M-_C0DqNDp3t1Ar0-bm-7M0yXtzwJoCapxigSQsmLR4w2ahBw',
        'domain': '.steamcommunity.com',
        'path': '/'
    }
    
    driver.add_cookie(steam_cookie)
    
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
        driver = initialize_driver()
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
            
def get_steam_price_history(market_hash_name):
    """Fetches price history from Steam Market."""
    driver = None
    try:
        driver = initialize_driver()

        # First, visit the main market listing to get necessary cookies
        listing_url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}"
        print(f"\nVisiting listing page first: {listing_url}")
        driver.get(listing_url)
        time.sleep(3)  # Wait for page to load and cookies to be set

        # Then get the price history
        price_history_url = "https://steamcommunity.com/market/pricehistory/"
        params = {
            'country': 'US',
            'currency': 1,
            'appid': 730,
            'market_hash_name': market_hash_name
        }
        
        query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        full_price_history_url = f"{price_history_url}?{query_string}"
        
        print(f"\nFetching price history from: {full_price_history_url}")
        
        driver.get(full_price_history_url)
        
        # Wait longer for the data to load
        time.sleep(5)
        
        try:
            # Get the raw JSON data from the page
            raw_data = driver.find_element(By.TAG_NAME, "pre").text
            print(f"\nRaw data received: {raw_data[:200]}...")
            
            # Check if we got an empty response
            if raw_data == '[]':
                print("Received empty data, trying alternative method...")
                # Try to get data from the market page directly
                driver.get(listing_url)
                time.sleep(3)
                
                # Execute JavaScript to get price history
                price_history = driver.execute_script("""
                    return g_rgPriceHistory || null;
                """)
                
                if price_history:
                    print("\nFound price history through JavaScript!")
                    return price_history
                else:
                    print("Could not find price history data")
                    return None
            
            # Parse the JSON data if we got a non-empty response
            data = json.loads(raw_data)
            if isinstance(data, dict) and 'prices' in data:
                prices = data['prices']
                print("\nPrice History (last 5 entries):")
                print(f"{'Date':<25} {'Price':>10} {'Volume':>8}")
                print("-" * 45)
                
                for entry in prices[-5:]:
                    date, price, volume = entry
                    print(f"{date:<25} ${price:>8.2f} {volume:>8}")
                return prices
            else:
                print(f"Unexpected data structure: {data}")
                return None
                
        except Exception as e:
            print(f"Failed to parse price history data: {e}")
            if 'raw_data' in locals():
                print(f"Raw data was: {raw_data}")
            return None

    except Exception as e:
        print(f"Error fetching price history: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()


# Function to scrape the first 5 skin prices from Skinport with Cheapest First sorting
def scrape_skinport_skin_prices(skin_name, wear_condition=None):
    driver = None
    try:
        driver = initialize_driver()
        
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
                
                # time.sleep(3)  # Ensure dynamic content has fully loaded
                
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
            
            # time.sleep(3)
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
            
    

