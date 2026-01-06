from geopy.geocoders import Nominatim
import time

# Use a unique user agent
geolocator = Nominatim(user_agent="UnionBankListingScraperErson", timeout=10)

address = "Barangay Majada Calamba City, Province Of Laguna"
location = geolocator.geocode(address)

if location:
    print(f"Address: {location.address}")
    print(f"Latitude: {location.latitude}")
    print(f"Longitude: {location.longitude}")
else:
    print("Address not found or geocoding failed.")

time.sleep(1)  # respect usage policy