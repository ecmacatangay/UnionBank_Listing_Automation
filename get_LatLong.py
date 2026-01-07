
# geocode_csv_5th_column_nulls.py
import pandas as pd
import time
from typing import Optional, Dict
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ---- Settings ----
INPUT_CSV = "titles.csv"         # <-- change to your source CSV path
OUTPUT_CSV = "listings_geocoded.csv"
MIN_DELAY_SECONDS = 1.0            # Nominatim policy: 1 request/second
MAX_RETRIES = 2                    # retry on transient errors

def read_5th_column_as_address(filepath: str) -> pd.DataFrame:
    """
    Read the CSV and create a normalized 'address' column sourced from the 6th column
    (column POSITION, 0-based index 5), regardless of its header name.
    """
    df = pd.read_csv(filepath)
    if df.shape[1] < 6:
        raise ValueError("CSV must have at least 6 columns to use the 6th column as address.")

    # 5th column by position
    # fifth_col_name = df.columns[5]   # for logging/reference
    # df = df.copy()
    # df["address_COPY"] = df.iloc[:, 5].astype(str).str.strip()

    # Keep all rows (even if address is empty); we'll mark failed geocodes as NULL
    return df#, fifth_col_name

def geocode_addresses_no_hint_with_nulls(
    df: pd.DataFrame,
    min_delay_seconds: float = 1.0,
    max_retries: int = 2    
) -> pd.DataFrame:
    """
    Geocode df['address'] → df['lat'], df['long'] using Nominatim.
    Does NOT append any country hint. Respects usage policy via RateLimiter.
    Returns NULL (as pandas.NA) for lat/long when geocoding fails.
    """
    geolocator = Nominatim(user_agent="my_Geocoder_App-Erson", timeout=10)
    rate_geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=min_delay_seconds,
        swallow_exceptions=False
    )

    cache: Dict[str, Optional[tuple]] = {}
    lats, longs = [], []

    for i, raw in enumerate(df["Title"].astype(str)):
        query = raw.strip()  # no country hint

        # Cache repeated addresses to save requests
        if query in cache:
            loc = cache[query]
        else:
            loc = None
            attempt = 0
            while attempt <= max_retries:
                try:
                    result = rate_geocode(query, addressdetails=False)
                    if result:
                        loc = (result.latitude, result.longitude)
                    else:
                        loc = None
                    break
                except Exception:
                    attempt += 1
                    time.sleep(min_delay_seconds + attempt * 0.5)  # backoff
            cache[query] = loc

        if loc is not None:
            lat, lon = loc
            lats.append(lat)
            longs.append(lon)
        else:
            # Use pandas.NA; will be written as "NULL" in CSV
            lats.append(pd.NA)
            longs.append(pd.NA)

        # Progress log every 10 rows
        if (i + 1) % 10 == 0:
            print(f"Geocoded {i+1}/{len(df)} addresses…")

    # Assign (do NOT drop rows)
    df["lat"] = lats
    df["long"] = longs  # requested naming

    # Optional safety: clip only non-null values
    df.loc[df["lat"].notna(), "lat"] = df.loc[df["lat"].notna(), "lat"].astype(float).clip(-90, 90)
    df.loc[df["long"].notna(), "long"] = df.loc[df["long"].notna(), "long"].astype(float).clip(-180, 180)

    return df

def main():
    df_src= read_5th_column_as_address(INPUT_CSV)
    print(f"Loaded {len(df_src)} rows from {INPUT_CSV}." )
      
        #Using 5th column '{fifth}' as address input (no country hint).")

    df_geo = geocode_addresses_no_hint_with_nulls(
        df_src,
        min_delay_seconds=MIN_DELAY_SECONDS,
        max_retries=MAX_RETRIES
    )

    # Save output CSV: original columns + address + lat + long
    # Represent missing values as literal "NULL" in the CSV
    df_geo.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig", na_rep="NULL")
    print(f"Saved geocoded CSV: {OUTPUT_CSV} ({len(df_geo)} rows; failures marked as NULL)")

if __name__ == "__main__":
    main()
