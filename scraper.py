from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import time

# Define the URL of the marketplace to scrape
URL = 'https://steamcommunity.com/market/search'

# Selenium setup
FIREFOX_DRIVER_PATH = r'C:\\WebDrivers\\geckodriver.exe'  # Updated path with raw string
FIREFOX_BINARY_PATH = r'C:\\Program Files\\Mozilla Firefox\\firefox.exe'  # Adjust if Firefox is in a different location

# Define headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
    'Accept-Language': 'en-US,en;q=0.9'
}

# Function to scrape skin prices using Selenium and BeautifulSoup
def scrape_skin_prices(skin_name):
    driver = None
    try:
        # Set Firefox options
        options = Options()
        options.binary_location = FIREFOX_BINARY_PATH
        
        service = Service(FIREFOX_DRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
        driver.get(URL)
        
        # Wait for the search box to load
        time.sleep(3)
        search_box = driver.find_element(By.ID, 'findItemsSearchBox')
        search_box.clear()
        search_box.send_keys(skin_name)
        
        # Click the search button
        search_button = driver.find_element(By.ID, 'findItemsSearchSubmit')
        search_button.click()
        
        # Wait for search results to load
        time.sleep(5)
        
        # Get page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract relevant data (based on marketplace's HTML structure)
        prices = []
        for item in soup.find_all('div', class_='market_listing_row'):  # Adjust class based on actual structure
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

# Example usage
if __name__ == '__main__':
    skin_name = input("Enter the name of the skin: ")
    results = scrape_skin_prices(skin_name)
    
    if results:
        for idx, skin in enumerate(results, start=1):
            print(f"{idx}. {skin['name']} - {skin['price']}")
    else:
        print("No skins found or an error occurred.")
