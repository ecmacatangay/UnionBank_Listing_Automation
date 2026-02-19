import pandas as pd, os, numpy as np
import folium
ROOT = r"D:\Desktop\Python\Web_Scraping"
PATH = "UnionBank_Listing_Automation"
FILENAME = "listings_geocoded.csv"
FILE_PATH = os.path.join(ROOT, PATH, FILENAME)
def main():

 df = pd.read_csv(FILE_PATH)

 m = folium.Map(location=[14.583, 121.063], zoom_start=13, tiles="OpenStreetMap")


 for _, row in df.iterrows():
      # Skip rows where lat or long is NaN
      if pd.isna(row["lat"]) or pd.isna(row["long"]):
          continue

      popup_html = f"""
        <div style="width:240px">
            <h4 style="margin:0">{row['Title']}</h4>
            <h5 style="margin:0">{row['Lot Description']}</h5>
            <p style="margin:0">₱{row['Price']:,.0f} — {row['Lot']} sqm</p>
            <img src="{row['Image_Link']}" width="220" style="margin-top:5px"/>
            <h5 style="margin-top:10px">
                <a href="{row['Link']}" target="_blank">View Listing</a>
            </h5>
        </div>
        """


      folium.Marker(
          location=[row["lat"], row["long"]],
          popup=folium.Popup(popup_html, max_width=260),
          tooltip="Click for photo",
          icon=folium.Icon(color="darkblue", icon="home")
      ).add_to(m)
      m.save("index.html")



print("Saved map_markers.html (tip: serve via `python -m http.server 8000` and open http://localhost:8000/map_markers.html)")

if __name__ == "__main__":
    main()
