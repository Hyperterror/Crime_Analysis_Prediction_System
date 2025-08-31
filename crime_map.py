import pandas as pd
import folium
from folium.plugins import MarkerCluster

# Load crime data (Ensure 'Lat', 'Long', and 'offence' columns exist)
data = pd.read_csv("./data/MCI_2014_to_2019.csv")

# Group by location and count crimes
crime_counts = data.groupby(["Lat", "Long"]).size().reset_index(name="crime_count")

# Create a base map centered around India
crime_map = folium.Map(location=[22.0, 78.0], zoom_start=5)

# Add Marker Clustering
marker_cluster = MarkerCluster().add_to(crime_map)

# Function to determine marker color based on crime count
def get_marker_color(crime_count):
    if crime_count > 100:
        return "darkred"
    elif crime_count > 50:
        return "red"
    elif crime_count > 20:
        return "orange"
    elif crime_count > 10:
        return "yellow"
    else:
        return "green"

# Add crime locations with color-coded markers and crime count
for _, row in crime_counts.iterrows():
    folium.CircleMarker(
        location=[row["Lat"], row["Long"]],
        radius=5 + (row["crime_count"] / 20),  # Increase size for higher crime count
        color=get_marker_color(row["crime_count"]),
        fill=True,
        fill_color=get_marker_color(row["crime_count"]),
        fill_opacity=0.7,
        popup=f"Crimes: {row['crime_count']}",
    ).add_to(marker_cluster)

# Save and display the map
crime_map.save("crime_map.html")
print("Crime map generated! Open 'crime_map.html' in your browser.")
