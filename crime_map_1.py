import pandas as pd
import folium
from folium.plugins import MarkerCluster

data = pd.read_csv("data/processed_data.csv")

# Group by location and count crimes
crime_counts = data.groupby(["Lat", "Long"]).size().reset_index(name="crime_count")
crime_map = folium.Map(location=[-79.35, 43.65], zoom_start=5)
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
        radius=5 + (row["crime_count"] / 20),
        color=get_marker_color(row["crime_count"]),
        fill=True,
        fill_color=get_marker_color(row["crime_count"]),
        fill_opacity=0.7,
        popup=f"Crimes: {row['crime_count']}",
    ).add_to(marker_cluster)

crime_map.save("crime_map_1.html")
print("Crime map generated! Open 'crime_map_1.html' in your browser.")