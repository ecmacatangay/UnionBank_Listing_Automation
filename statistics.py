
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from typing import Optional, Dict

# ----------------------------
# 1) Load data (CSV/XLS/XLSX)
# ----------------------------
def load_data(filepath: str) -> pd.DataFrame:
    fp = filepath.lower()
    if fp.endswith(".xlsx"):
        df = pd.read_excel(filepath, engine="openpyxl")
    elif fp.endswith(".xls"):
        df = pd.read_excel(filepath, engine="xlrd")
    elif fp.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        raise ValueError("Unsupported file format. Please upload CSV or Excel.")
    return df

# ------------------------------------------
# 2) Clean, standardize, derive base metrics
# ------------------------------------------
def prepare_data_with_address_lot_price(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Standardize column names
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"[\s\-]+", "_", regex=True)
    )

    # Expected columns: address, lot, price
    col_map = {}

    # Flexible mapping: handle common variants
    # Address
    for c in df.columns:
        if c in ["address", "location", "city", "area", "barangay", "district", "site_address"]:
            col_map[c] = "address"
            break
    # Lot (sqm)
    for c in df.columns:
        if c in ["lot", "lot_area", "sqm", "square_meter", "square_meters", "floor_area", "area_sqm"]:
            col_map[c] = "lot"
            break
    # Price
    for c in df.columns:
        if c in ["price", "total_price", "listing_price", "amount", "cost"]:
            col_map[c] = "price"
            break

    df = df.rename(columns=col_map)

    required = ["address", "lot", "price"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. "
                         "Please ensure your file has Address, Lot, and Price.")

    # Coerce numeric BEFORE calculations
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["lot"] = pd.to_numeric(df["lot"], errors="coerce")

    # Basic cleaning (remove NaNs, zeros, and infs)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["price", "lot", "address"])
    df = df[(df["price"] > 0) & (df["lot"] > 0)]

    # Derive price per sqm
    df["price_per_sqm"] = df["price"] / df["lot"]

    # Optional: trim extreme outliers in ₱/sqm using IQR
    if df["price_per_sqm"].notna().sum() > 0:
        q1, q3 = df["price_per_sqm"].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = max(q1 - 1.5 * iqr, df["price_per_sqm"].min())
        upper = q3 + 1.5 * iqr
        df = df[(df["price_per_sqm"] >= lower) & (df["price_per_sqm"] <= upper)]

    # Tidy address
    df["address"] = df["address"].astype(str).str.strip()

    return df

# -----------------------------------------------------
# 3) Scoring + ranking (budget + location preferences)
# -----------------------------------------------------
def rank_top10(
    df: pd.DataFrame,
    budget: Optional[float] = None,
    location_prefs: Optional[Dict[str, float]] = None,
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    df = df.copy()

    # Budget filter
    if budget is not None:
        df = df[df["price"] <= budget]

    if df.empty:
        raise ValueError("No listings left after filtering. Adjust budget or check data.")

    # Default weights
    weights = weights or {"value": 0.6, "size": 0.3, "location": 0.1}

    # Normalize price_per_sqm (lower better → higher score)
    v_min, v_max = df["price_per_sqm"].min(), df["price_per_sqm"].max()
    df["value_score"] = 1.0 if v_max == v_min else 1 - (df["price_per_sqm"] - v_min) / (v_max - v_min)

    # Normalize lot size (higher better)
    s_min, s_max = df["lot"].min(), df["lot"].max()
    df["size_score"] = 1.0 if s_max == s_min else (df["lot"] - s_min) / (s_max - s_min)

    # Location preference mapping (match by address string contains key)
    if location_prefs:
        def loc_bonus(addr: str) -> float:
            addr_l = str(addr).lower()
            for k, v in location_prefs.items():
                if str(k).lower() in addr_l:
                    return float(v)
            return 0.0
        df["location_score"] = df["address"].map(loc_bonus)
    else:
        df["location_score"] = 0.0

    # Composite score
    df["score"] = (
        weights["value"] * df["value_score"] +
        weights["size"] * df["size_score"] +
        weights["location"] * df["location_score"]
    )

    # Final ranking
    top10 = df.sort_values("score", ascending=False).head(10).copy()

    # Helpful formatted columns
    top10["price_fmt"] = top10["price"].map(lambda x: f"₱{x:,.0f}")
    top10["price_per_sqm_fmt"] = top10["price_per_sqm"].map(lambda x: f"₱{x:,.0f}/sqm")
    top10["lot_fmt"] = top10["lot"].map(lambda x: f"{x:,.2f} sqm")

    return top10

# -----------------------------------
# 4) Summary by location (benchmark)
# -----------------------------------
def summarize_by_address(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    # Aggregate by full address. If you want city-level, pre-parse a city column.
    agg = df.groupby("address", as_index=False).agg(
        listings=("address", "count"),
        median_price_per_sqm=("price_per_sqm", "median"),
        median_price=("price", "median"),
        median_lot=("lot", "median"),
    )
    return agg.sort_values("median_price_per_sqm").head(top_n)

# -------------------------------------
# 5) Plot Top 10 scores (bar chart)
# -------------------------------------
def plot_top10(top10: pd.DataFrame, label_col: str = "address", fname: str = "top10_scores.png"):
    plt.figure(figsize=(10, 6))
    labels = top10[label_col]
    plt.barh(labels, top10["score"], color="#2a9d8f")
    plt.xlabel("Composite Score (higher is better)")
    plt.ylabel("Listing (Address)")
    plt.title("Top 10 Listings — Composite Score")
    plt.gca().invert_yaxis()
    # annotate price per sqm
    
    for i, (score, ppsqm) in enumerate(zip(top10["score"], top10["price_per_sqm_fmt"])):
        plt.text(score + 0.005, i, ppsqm, va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()

# -------------------------
# 6) Main analysis function
# -------------------------
def analyze_file(filepath: str,
                 budget: Optional[float] = None,
                 location_prefs: Optional[Dict[str, float]] = None,
                 weights: Optional[Dict[str, float]] = None):
    df = load_data(filepath)
    df_clean = prepare_data_with_address_lot_price(df)

    top10 = rank_top10(
        df_clean,
        budget=budget,
        location_prefs=location_prefs,
        weights=weights
    )

    # Simple summary (cheapest addresses by median ₱/sqm)
    addr_summary = summarize_by_address(df_clean, top_n=20)

    # Export results
    with pd.ExcelWriter("analysis_output.xlsx", engine="openpyxl") as writer:
        df_clean.to_excel(writer, index=False, sheet_name="Cleaned_Data")
        top10.to_excel(writer, index=False, sheet_name="Top10")
        addr_summary.to_excel(writer, index=False, sheet_name="Address_Summary")

    # Plot chart
    plot_top10(top10, label_col="address", fname="top10_scores.png")

    return {
        "top10": top10[["address", "price_fmt", "price_per_sqm_fmt", "lot_fmt", "score"]],
        "address_summary": addr_summary
    }


def main():
    results = analyze_file(
        "clean_real_estate.csv",                     # <-- replace with your file name/path
        budget=6_000_000,                   # optional
       # location_prefs={"NCR": 0.5},  # optional boosts
        weights={"value": 0.5, "size": 0.3, "location": 0.2}  # optional tuning
    )
    print(results["top10"])
    print(results["address_summary"])
# ---------- Example Usage ----------
if __name__ == "__main__":
    main()
