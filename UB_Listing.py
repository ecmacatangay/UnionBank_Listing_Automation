
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException,
    ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException
)
from urllib.parse import urlparse, parse_qs
import time, csv
asdasd
# Keep Chrome Browser Open
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=chrome_options)

driver.set_page_load_timeout(30)
driver.get("https://www.unionbankph.com/foreclosed-properties?page=1&min_bid_price=0&max_bid_price=0&type_of_property=Residential&type_of_residential=House%20and%20Lot&location=&city=&lot_area=0&floor_area=0&sort_by_price=")

wait = WebDriverWait(driver, 15)

clicks = 0
max_clicks = 5  # safety cap
per_click_timeout = 10


price_collections = []
address_collections = []
lot_collections = []
link_collections = []
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
                "Link":link_collections[i]
            }
            
        for x, y in listings.items():
         print(y['Address'], y['Lot'],y['Price'],y['Link'])
            # 1) Locate the RIGHT ARROW'S clickable ancestor reliably each loop
            # Prefer an anchor <a> or button <button> ancestor of the SVG
            # Try anchor first (most paginations use links)
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
print(len(listings))
list_collection = list(listings.values())
#items_list = list(my_dict.items())


# Save to CSV

with open("listings.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["Address", "Lot", "Price","Link"])
    writer.writeheader()
    writer.writerows(list_collection)

print("Done.")


