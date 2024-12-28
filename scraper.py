from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Define the URLs of the marketplaces to scrape
STEAM_URL = 'https://steamcommunity.com/market/search'
SKINPORT_URL = 'https://skinport.com/market?search='

# Selenium setup
FIREFOX_DRIVER_PATH = r'C:\WebDrivers\geckodriver.exe'  # Updated path to GeckoDriver
FIREFOX_BINARY_PATH = r'C:\Program Files\Mozilla Firefox\firefox.exe'

# Define headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
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

# Function to initialize the Firefox driver with proper options
def initialize_driver():
    options = Options()
    options.binary_location = FIREFOX_BINARY_PATH
    service = Service(FIREFOX_DRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)
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
        
        time.sleep(5)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        prices = []
        for item in soup.find_all('div', class_='market_listing_row'):
            name_tag = item.find('span', class_='market_listing_item_name')
            price_tag = item.find('span', class_='normal_price')
            
            if name_tag and price_tag:
                name = name_tag.text.strip()
                price = price_tag.text.strip()
                prices.append({'name': name, 'price': price})
        
        return prices
    
    except Exception as err:
        print(f"An error occurred: {err}")
    finally:
        if driver:
            driver.quit()

# Function to scrape the first skin price from Skinport with wear filter
def scrape_skinport_skin_price(skin_name, wear_condition=None):
    driver = None
    try:
        driver = initialize_driver()
        search_query = f"{skin_name} {wear_condition}" if wear_condition and wear_condition.lower() != 'all' else skin_name
        search_query = search_query.replace(' ', '+')
        search_url = f"https://skinport.com/market?search={search_query}"
        driver.get(search_url)
        print(f"Navigated to: {search_url}")
        
        # Handle cookie popup
        handle_cookie_popup(driver)
        print("Handled cookie popup")
        
        # Ensure items are loaded
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'CatalogPage-items'))
        )
        print("Items grid loaded")
        
        # Wait for first CatalogPage-item to load
        first_item = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.CatalogPage-item'))
        )
        print("First item located")
        
        # Extract item name and price
        try:
            name = first_item.find_element(By.CSS_SELECTOR, '.ItemPreview-itemName').text.strip()
            price = first_item.find_element(By.CSS_SELECTOR, '.Tooltip-link').text.strip()
            print(f"Found: {name}, {price}")
            return {'name': name, 'price': price}
        except Exception as e:
            print(f"Failed to extract data for the first item: {e}")
        
        return None
    
    except Exception as err:
        print(f"An error occurred: {err}")
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
    else:
        print("No skins found on Steam.")

    print("\n--- Skinport Marketplace Results ---")
    skinport_result = scrape_skinport_skin_price(skin_name, wear_condition)
    if skinport_result:
        print(f"1. {skinport_result['name']} - {skinport_result['price']}")
    else:
        print("No skins found on Skinport.")
