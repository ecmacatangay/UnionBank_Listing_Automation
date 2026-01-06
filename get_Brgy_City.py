
# selenium_extract_titles.py
import time,os,re, Testing
import pandas as pd
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


ROOT = r"D:\Desktop\Python\Web_Scraping"
PATH = "UnionBank_Listing_Automation"
FILENAME = "clean_real_estate.csv"

# Construct the full path
FILE_PATH = os.path.join(ROOT, PATH, FILENAME)


INPUT_CSV = FILE_PATH     # <-- change to your file path
OUTPUT_CSV = "titles.csv"
DELAY_SECONDS = 1.0            # polite delay between pages
MAX_RETRIES = 2                 # retries per URL
PAGE_LOAD_TIMEOUT = 25          # seconds
def make_driver(headless=True, proxy=None):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    # disguise automation
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def extract_title_with_selenium(driver: webdriver.Chrome) -> Optional[str]:
    """
    Try to extract a clean title from:
      1) <meta property="og:title">
      2) <title>
      3) first <h1>
    """
    # 1) og:title via JS
    try:
        og = driver.execute_script(
            "return document.querySelector('meta[property=\"og:title\"]')?.content || null;"
        )
        if og and isinstance(og, str) and og.strip():
            return og.strip()
    except WebDriverException:
        pass

    # 2) <title>
    try:
        raw_title = driver.title
        if raw_title and raw_title.strip():
            return raw_title.strip()
    except WebDriverException:
        pass

    # 3) first <h1>
    try:
        # Wait a bit for h1 if the site is JS-heavy
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        except Exception:
            pass
        h1 = driver.find_element(By.TAG_NAME, "h1")
        h1_text = h1.text.strip()
        if h1_text:
            return h1_text
    except (NoSuchElementException, WebDriverException):
        pass

    return None

def fetch_title(driver: webdriver.Chrome, url: str) -> str:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            driver.get(url)

            # Small wait to allow JS/meta tags to be populated
            time.sleep(1.5)

            title = extract_title_with_selenium(driver)
            if title:
                return title
            else:
                return "(no title)"
        except (WebDriverException, TimeoutException) as e:
            last_err = e
            time.sleep(DELAY_SECONDS + attempt * 0.5)
    return f"(error) {type(last_err).__name__}: {last_err}"



def read_links_column(df: pd.DataFrame) -> pd.Series:
    """
    Return the Series containing links.
    Prefer 'Link' column if present; otherwise fall back to the 4th column by position.
    """
    if "Link" in df.columns:
        return df["Link"].astype(str).str.strip()
    else:
        if df.shape[1] < 4:
            raise ValueError("CSV does not have a 4th column and 'Link' column is missing.")
        return df.iloc[:, 3].astype(str).str.strip()  # 0-based index: 3 = fourth column

def remove_after_pipe(text: str) -> str:
    """
    Removes everything after the first '|' in the given text.
    If '|' is not found, returns the original text.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    
    # Split at the first '|' and take the part before it
    remove_pipe = text.split('|', 1)[0].strip()

    match = re.search(r'(Barangay|BRGY|Brgy.|BRGY.|Barangays|BGY|Building|Brgys.|Barnagy|Subdivision,\
                      |Subdivision|Mansions,|Mansion|Executive,|Subdivision,)\s.*$', remove_pipe, flags=re.IGNORECASE)

    if match:
        result = match.group(0).strip()
        return result
        #print("Extracted:", result)
    else:
        return print("No match found")

def extract_lot_description(driver: webdriver.Chrome) -> str:
    """
    Extracts lot description from the page, typically from an <h1> or a known container.
    Returns 'Vacant Lot', 'House and Lot', or '(unknown)'.
    """
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.txt-container-2 h1"))
        )
        h1 = driver.find_element(By.CSS_SELECTOR, "div.txt-container-2 h1")
        text = h1.text.strip().lower()
        if "vacant lot" in text:
            return "Vacant Lot"
        elif "townhouse" in text:
            return "Town House"
        elif "condominium" in text:
            return "Condominium"
        elif "house and lot" in text:
            return "House and Lot"
    except Exception:
        pass
    return "(unknown)"


def main():
    # 1) Read CSV
    df = pd.read_csv(INPUT_CSV)
    links = read_links_column(df)
    links = links.dropna()
    # Optional: de-duplicate by link
    mask_valid = links.str.startswith("http")
    df = df.loc[mask_valid].copy()
    df["Link"] = links.loc[mask_valid].values

    # 2) Selenium driver
    driver = make_driver(headless=True, proxy=None)
    titles = []
    lot_descriptions = []

    try:
     for i, url in enumerate(df["Link"], 1):
        print(f"[{i}/{len(df)}] {url}")
        driver.get(url)
        time.sleep(1.5)

        title = extract_title_with_selenium(driver)
        cleaned_title = remove_after_pipe(title)
        titles.append(cleaned_title)

        lot_type = extract_lot_description(driver)
        lot_descriptions.append(lot_type)

        time.sleep(DELAY_SECONDS)
    finally:
     driver.quit()


    # 4) Save output with original columns + Title
    df_out = df.copy()
    # result = remove_after_pipe(sample)
    df_out["Title"] = titles
    df_out["Lot Description"]  = lot_descriptions

    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Saved {OUTPUT_CSV} with {len(df_out)} rows.")

if __name__ == "__main__":
    main()

