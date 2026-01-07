from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException,
    ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException
)
from urllib.parse import urlparse, parse_qs
import time, csv, os, pandas as pd, re
from datetime import datetime
from datetime import datetime
import time, get_Brgy_City, statistics, get_LatLong, Testing
# import get_Brgy_City, statistics, get_LatLong

now = datetime.now()
print(f"Execution starts: {now}")

# Keep Chrome Browser Open
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=chrome_options)

driver.set_page_load_timeout(30)
driver.get("https://www.unionbankph.com/foreclosed-properties?page=1&min_bid_price=0&max_bid_price=0&type_of_property=Residential&type_of_residential=House%20and%20Lot&location=&city=&lot_area=0&floor_area=0&sort_by_price=")

wait = WebDriverWait(driver, 15)

clicks = 0
max_clicks = 12  # safety cap
per_click_timeout = 10



price_collections = []
address_collections = []
lot_collections = []
link_collections = []
img_collections = []
listings = {}

def current_page_number():
    # Parse the ?page=N from current URL; default to 1 if missing
    parsed = urlparse(driver.current_url)
    qs = parse_qs(parsed.query)
    try:
        return int(qs.get("page", ["1"])[0])
    except Exception:
        return 1

while clicks < max_clicks:
    try:

        lot_field = driver.find_elements(By.CSS_SELECTOR, "p.specs")
        address_field = driver.find_elements(By.CSS_SELECTOR, "p.city-arg")
        price_field = driver.find_elements(By.CSS_SELECTOR,"p.price")
       # link_field = driver.find_elements(By.CSS_SELECTOR,value='a ')
        link_field = driver.find_elements(By.XPATH, "//a[contains(@href, 'foreclosed-properties')]")
     

        # Print the href values
        for link in link_field:
            href=link.get_attribute("href")
            link_collections.append(href)
            img = link.find_element(By.TAG_NAME, "img") 
            src = img.get_attribute("src") 
            img_collections.append(src)
            
        for address in address_field:
            address_collections.append(address.text)

        for lot in lot_field:
            lot_collections.append(lot.text)

        for price in price_field:
            price_collections.append(price.text)

        for i in range(len(address_collections)):
            listings[i] = {
                "Address":address_collections[i],
                "Lot":lot_collections[i],
                "Price":price_collections[i],
                "Image_Link":img_collections[i],
                "Link":link_collections[i]
            }
            

        try:
            target = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//*[name()='svg' and @data-icon='right']/ancestor::a[1]")
            ))
        except TimeoutException:
            # Fallback to button ancestor
            target = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//*[name()='svg' and @data-icon='right']/ancestor::button[1]")
            ))

        # If it is disabled or hidden, stop
        aria_disabled = target.get_attribute("aria-disabled")
        disabled_attr = target.get_attribute("disabled")
        if (aria_disabled and aria_disabled.strip().lower() == "true") or (disabled_attr is not None) or (not target.is_displayed()):
            print(f"Stopped: Next control disabled/hidden. Total clicks: {clicks}")
            break

        # 2) Wait until clickable & scroll into view
        target = WebDriverWait(driver, per_click_timeout).until(EC.element_to_be_clickable(
            (By.XPATH, "//*[name()='svg' and @data-icon='right']/ancestor::*[self::a or self::button][1]")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)

        # Record current page before clicking
        before_page = current_page_number()

        # 3) Click (prefer native click; fallback to synthetic click for stubborn components)
        try:
            target.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            # Dispatch a synthetic click (works for SVG-heavy UIs)
            driver.execute_script("""
                const el = arguments[0];
                el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
            """, target)

        # 4) Wait for "page changed" — either URL `page` increments OR content updates
        #    Here we wait for URL ?page to increase
        WebDriverWait(driver, 15).until(lambda d: current_page_number() > before_page)

        clicks += 1
        print(f"Moved from page {before_page} to {current_page_number()} (click {clicks})")

        # Optional: small sleep to let heavy content settle (avoid race with re-enabling Next)
        time.sleep(0.5)

    except TimeoutException:
        print(f"Stopped: Next not clickable / page did not change in time. Total clicks: {clicks}")
        break
    except StaleElementReferenceException:
        # DOM refreshed while clicking; just retry next iteration
        continue
    except NoSuchElementException:
        print(f"Stopped: Next control not found. Total clicks: {clicks}")
        break
print(f"There are {len(listings)} records")
list_collection = list(listings.values())

root = r"D:\Desktop\Python\Web_Scraping"
path = "UnionBank_Listing_Automation"
filename = "listings.csv"

# Construct the full path
file_path = os.path.join(root, path, filename)

# Open the file for writing
with open(file_path, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["Address", "Lot", "Price","Image_Link","Link"])
    writer.writeheader()
    writer.writerows(list_collection)

file_path = os.path.join(root, path, filename)

df = pd.read_csv(file_path, encoding="utf-8")


def clean_real_estate_data():
    """
    Cleans Address, Lot, and Price columns:
    - Address: extracts Province only
    - Lot: extracts LA if present, else FA, converts to numeric
    - Price: removes Php/₱, commas, converts to numeric
    """
    # --- Clean Address (Province only) ---
    
    df['Address'] = df['Address'].str.split(",").str[-1].str.strip()
    # --- Clean Lot ---
    def extract_area(text):
        la_match = re.search(r'LA:\s*(\d+)', str(text))
        if la_match:
            return la_match.group(1)
        fa_match = re.search(r'FA:\s*(\d+)', str(text))
        if fa_match:
            return fa_match.group(1)
        return None
    
    df['Lot'] = df['Lot'].apply(extract_area)
    df['Lot'] = df['Lot'].str.replace("sqm","",regex=False)  # remove unit
    df['Lot'] = df['Lot'].str.replace(",","")                # remove commas
    df['Lot'] = pd.to_numeric(df['Lot'], errors='coerce')    # convert to number
    
    # --- Clean Price ---
    df['Price'] = df['Price'].str.replace("Php","",regex=False)
    df['Price'] = df['Price'].str.replace("₱","",regex=False)
    df['Price'] = df['Price'].str.replace(",","")            # remove commas
    df['Price'] = df['Price'].str.strip()                    # remove spaces
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce') # convert to number
    
    return df

#Save Clean Data
df = clean_real_estate_data()
df = df.drop_duplicates(subset=["Address", "Price"])

clean_data_fname = "clean_real_estate.csv"
# Construct the full path
file_path = os.path.join(root, path, clean_data_fname)

df.to_csv(file_path,index=False)

after = datetime.now()

print(f"Time Completed: {after-now}")

print(f"Get Barangay City Started: {now}")
get_Brgy_City.main()
print(f"Get Barangay City Time Completed: {after-now}")
print(f"Statistics Execution Process Started {now}")
statistics.main()
print(f"Statistics Process Completed: {after-now}")
print(f"Getting Lat Long Started {now}")
get_LatLong.main()
print(f"Lat Long Process Completed: {after-now}")
print(f"Creating MAPPING Started {now}")
Testing.main()
print(f"MAP Creation Completed: {after-now}")