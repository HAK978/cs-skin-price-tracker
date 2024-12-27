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
SKINPORT_URL = 'https://skinport.com'

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

# Function to scrape skin prices from Skinport with wear filter
def scrape_skinport_skin_prices(skin_name, wear_condition=None):
    driver = None
    try:
        driver = initialize_driver()
        driver.get(SKINPORT_URL)
        
        # Handle cookie popup
        handle_cookie_popup(driver)
        
        # Wait for the search input to be visible
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'searchInput'))
        )
        
        search_box.clear()
        search_query = f"{skin_name} {wear_condition}" if wear_condition and wear_condition.lower() != 'all' else skin_name
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        
        time.sleep(5)
        
        # Apply cheapest-first sorting
        sort_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.Dropdown-button'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", sort_button)
        sort_button.click()
        time.sleep(2)
        cheapest_option = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Cheapest first')]"))
        )
        cheapest_option.click()
        time.sleep(3)
        
        # Get the first skin listing
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        item = soup.find('div', class_='ItemPreview')
        if item:
            name_tag = item.find('a', class_='ItemPreview-href')
            price_tag = item.find('div', class_='Tooltip-link')
            wear_tag = item.find('div', class_='ItemPreview-itemText')
            float_tag = item.find('div', class_='WearBar-value')
            
            if name_tag and price_tag:
                name = name_tag.text.strip()
                price = price_tag.text.strip()
                wear = wear_tag.text.strip() if wear_tag else 'N/A'
                float_value = float_tag.text.strip() if float_tag else 'N/A'
                return {'name': name, 'price': price, 'wear': wear, 'float': float_value}
        
        return None
    
    except Exception as err:
        print(f"An error occurred: {err}")
    finally:
        if driver:
            driver.quit()

# Example usage
if __name__ == '__main__':
    skin_name = input("Enter the name of the skin: ")
    wear_condition = input(f"Enter the wear condition (FN/MW/FT/WW/BS/All): ").strip().lower()
    wear_condition = WEAR_CONDITIONS.get(wear_condition, 'all')
    
    print("--- Steam Marketplace Results ---")
    steam_results = scrape_steam_skin_prices(skin_name, wear_condition)
    if steam_results:
        for idx, skin in enumerate(steam_results, start=1):
            print(f"{idx}. {skin['name']} - {skin['price']}")
    else:
        print("No skins found on Steam.")
    
    print("\n--- Skinport Marketplace Results ---")
    skinport_result = scrape_skinport_skin_prices(skin_name, wear_condition)
    if skinport_result:
        print(f"1. {skinport_result['name']} - {skinport_result['price']} (Wear: {skinport_result['wear']}, Float: {skinport_result['float']})")
    else:
        print("No skins found on Skinport.")
