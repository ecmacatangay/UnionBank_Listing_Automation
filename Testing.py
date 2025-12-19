import os,re
import pandas as pd
import matplotlib.pyplot as plt


root = r"D:\Desktop\Python\Web_Scraping"
path = "UnionBank_Listing_Automation"
gz_file = "listings.csv"

file_path = os.path.join(root, path, gz_file)

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
if __name__ == "__main__":
    # This part only runs if script_to_call.py is executed directly
    df = clean_real_estate_data()
print(df)