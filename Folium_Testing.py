import folium
import pandas as pd

# Example data with image URLs (replace with your own URLs or local paths)
df = pd.DataFrame({
    "address": ["Lot 14 Block 10, Goleta Street, Santa Barbara Subdivision, Barangay Kauswagan, Cagayan de Oro City, Misamis Oriental", "Kapitolyo, Pasig", "Tanza Cavite"],
    "lat": [14.586, 14.566, 14.301772],
    "lon": [121.060, 121.056, 120.816555],
    "price": [5_000_000, 4_200_000, 5_742_000],
    "lot": [120, 95, 718],
    "image_url": [
        "https://www.unionbankph.com/sites/default/files/2025-01/Screenshot%202025-01-13%20135843.png",
        "https://www.unionbankph.com/sites/default/files/2025-04/Capture1_65.PNG",
        "https://www.unionbankph.com/sites/default/files/2025-06/Capture1_24.PNG"
    ]
})

m = folium.Map(location=[14.583, 121.063], zoom_start=13, tiles="OpenStreetMap")

for _, row in df.iterrows():
    popup_html = f"""
    <div style="width:240px">
      <h4 style="margin:0">{row['address']}</h4>
      <p style="margin:0">₱{row['price']:,.0f} — {row['lot']} sqm</p>
      <img src="{row['image_url']}" width="220" style="margin-top:5px"/>
    </div>
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=260),
        tooltip="Click for photo",
        icon=folium.Icon(color="darkblue", icon="home")
    ).add_to(m)

m.save("map_markers.html")
print("Saved map_markers.html (tip: serve via `python -m http.server 8000` and open http://localhost:8000/map_markers.html)")
