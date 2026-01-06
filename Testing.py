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
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=chrome_options)

driver.set_page_load_timeout(30)
driver.get("https://www.unionbankph.com/foreclosed-properties?page=1&min_bid_price=0&max_bid_price=0&type_of_property=Residential&type_of_residential=House%20and%20Lot&location=&city=&lot_area=0&floor_area=0&sort_by_price=")

wait = WebDriverWait(driver, 15)
image_field = driver.find_elements(By.TAG_NAME, "img")
image_collections = []


# Print the href values
for img in image_field:
    src = img.get_attribute("src")
    image_collections.append(src)
  #  print(img.text)

print(len(image_collections))
print(image_collections)