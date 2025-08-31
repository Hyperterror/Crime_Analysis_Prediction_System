import flet as ft
import webbrowser
import pandas as pd
import requests
from geopy.distance import great_circle
import heapq
import atexit
import folium
from folium.plugins import MarkerCluster
from math import radians, sin, cos, sqrt, atan2
from auth import validate_login
from rate_limiter import is_rate_limited
from performance_model import performance_model_tab 

performance_tab = performance_model_tab()

# Load crime data
crime_data = pd.read_csv("data/processed_data.csv") 
junctions_data = pd.read_csv("data/junctions.csv")  

# Google Maps API key
API_KEY = "Google Maps API Key"

# Global variable to store optimized route
optimized_route = []

# Function to fetch roads data using Google Maps API
def fetch_roads_data(lat, long, radius=5000):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{long}&radius={radius}&type=route&key={API_KEY}"
    response = requests.get(url).json()
    roads = []
    for result in response.get("results", []):
        roads.append({
            "name": result["name"],
            "lat": result["geometry"]["location"]["lat"],
            "long": result["geometry"]["location"]["lng"]
        })
    return roads

# Function to calculate distance between two points using Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# A* Algorithm to find the shortest path
def a_star(start, goal, graph):
    open_set = []
    heapq.heappush(open_set, (0, start))  # Priority queue with (f_score, node)
    came_from = {}
    g_score = {start: 0}  # Cost from start to current node
    f_score = {start: haversine(start[0], start[1], goal[0], goal[1])}  # Estimated total cost
    
    while open_set:
        current_f, current = heapq.heappop(open_set)
        if current == goal:
            # Reconstruct the path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]  # Return reversed path
        
        # Explore neighbors
        if current not in graph:
            continue  # Skip if current node isn't in the graph
        
        for neighbor in graph[current]:
            # Calculate tentative g_score
            tentative_g_score = g_score.get(current, float('inf')) + haversine(current[0], current[1], neighbor[0], neighbor[1])
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                # This is a better path, update it
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + haversine(neighbor[0], neighbor[1], goal[0], goal[1])
                # Add neighbor to open set if not already present
                if neighbor not in [n for _, n in open_set]:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None  # No path found

# Create a graph from hotspots and police station
def create_graph(hotspots, police_station_lat, police_station_long):
    graph = {}
    hotspots_list = [(row["Lat"], row["Long"]) for _, row in hotspots.iterrows()]
    all_nodes = [(police_station_lat, police_station_long)] + hotspots_list
    # Fully connect the graph
    for node in all_nodes:
        graph[node] = [n for n in all_nodes if n != node]  # Connect each node to all others except itself
    return graph

def generate_patrol_route_map(police_station_lat, police_station_long, start_time, end_time):
    global optimized_route
    try:
        # Convert start_time and end_time to datetime objects
        from datetime import datetime
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        # Extract month and time slots
        crime_data["occurrencedate"] = pd.to_datetime(crime_data["occurrencedate"])
        crime_data["month"] = crime_data["occurrencedate"].dt.month
        crime_data["hour"] = crime_data["occurrencedate"].dt.hour
        
        # Filter crimes for the same month and time slots
        filtered_crimes = crime_data[
            (crime_data["month"] == start_time.month) &
            (crime_data["hour"] >= start_time.hour) &
            (crime_data["hour"] <= end_time.hour)
        ]
        print(f"Filtered crimes count: {len(filtered_crimes)}")  # Debug print
        
        if len(filtered_crimes) == 0:
            raise ValueError("No crimes found for the given month and time slots.")
        
        # Group by location and calculate average crime counts
        crime_avg = filtered_crimes.groupby(["Lat", "Long"]).size().reset_index(name="crime_count")
        crime_avg["crime_count"] = crime_avg["crime_count"] / len(filtered_crimes["occurrencedate"].dt.day.unique())
        print(f"Average crime counts: {crime_avg}")  # Debug print
        
        # Filter hotspots within a 5 km radius of the police station
        police_station = (police_station_lat, police_station_long)
        crime_avg["distance"] = crime_avg.apply(
            lambda row: haversine(police_station[0], police_station[1], row["Lat"], row["Long"]),
            axis=1
        )
        hotspots = crime_avg[crime_avg["distance"] <= 5]  # Filter within 5 km radius
        print(f"Hotspots within 5 km: {len(hotspots)}")  # Debug print
        
        if len(hotspots) == 0:
            raise ValueError("No hotspots found within 5 km of the police station.")
        
        # Find the nearest junction to the police station
        junctions_data["distance"] = junctions_data.apply(
            lambda row: haversine(police_station[0], police_station[1], row["Lat"], row["Long"]),
            axis=1
        )
        nearest_junction = junctions_data.loc[junctions_data["distance"].idxmin()]
        print(f"Nearest junction: {nearest_junction}")  # Debug print
        
        # Create a base map centered around the police station
        crime_map = folium.Map(location=[police_station_lat, police_station_long], zoom_start=13)
        marker_cluster = MarkerCluster().add_to(crime_map)
        
        # Add police station to the map
        folium.Marker(
            location=[police_station_lat, police_station_long],
            popup="Police Station",
            icon=folium.Icon(color="green", icon="home")
        ).add_to(crime_map)
        
        # Add nearest junction to the map
        folium.Marker(
            location=[nearest_junction["Lat"], nearest_junction["Long"]],
            popup=f"Nearest Junction {nearest_junction['Junction_ID']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(crime_map)
        
        # Add hotspots to the map
        for _, row in hotspots.iterrows():
            folium.CircleMarker(
                location=[row["Lat"], row["Long"]],
                radius=5,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.7,
                popup=f"Hotspot: {row['crime_count']:.2f} crimes/day"
            ).add_to(crime_map)
        
        # Create a list of all nodes (nearest junction + hotspots)
        all_nodes = [(nearest_junction["Lat"], nearest_junction["Long"])] + [
            (row["Lat"], row["Long"]) for _, row in hotspots.iterrows()
        ]
        
        # Create a fully connected graph
        graph = {}
        for node in all_nodes:
            graph[node] = [n for n in all_nodes if n != node]  # Connect each node to all others except itself
        
        # Solve the Traveling Salesman Problem (TSP) to find the optimal route
        from itertools import permutations
        def calculate_total_distance(path):
            total_distance = 0
            for i in range(len(path) - 1):
                total_distance += haversine(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
            return total_distance
        
        # Generate all possible paths (excluding the starting point)
        hotspots_nodes = all_nodes[1:]  # Exclude the nearest junction
        shortest_path = None
        shortest_distance = float('inf')
        
        # Use permutations to find the shortest path (brute-force TSP)
        for path in permutations(hotspots_nodes):
            path = [all_nodes[0]] + list(path)  # Start and end at the nearest junction
            distance = calculate_total_distance(path)
            if distance < shortest_distance:
                shortest_distance = distance
                shortest_path = path
        
        # Add optimized route to the map
        if shortest_path:
            folium.PolyLine(
                locations=shortest_path,
                color="red",
                weight=5,
                opacity=0.7,
                popup="Optimized Patrol Route"
            ).add_to(crime_map)
        
        # Save the map
        crime_map.save("optimized_patrol_route.html")
        print("Optimized patrol route map generated! Opening in browser...")
        # Automatically open the map in the default browser
        webbrowser.open("optimized_patrol_route.html")
        
    except Exception as ex:
        print(f"Error in generate_patrol_route_map: {ex}")  # Debug print
        raise ex

# Modern Theme Configuration
def apply_modern_theme(page: ft.Page):
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.colors.BLUE,
        visual_density=ft.ThemeVisualDensity.COMFORTABLE,
    )
    page.fonts = {
        "RobotoSlab": "https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@300;400;500;700&display=swap"
    }

# Modern Login Page
def create_login_page(page: ft.Page, show_dashboard_callback):
    username_field = ft.TextField(
        label="Username",
        width=350,
        prefix_icon=ft.icons.PERSON,
        border_radius=15,
        filled=True,
        bgcolor=ft.colors.GREY_50,
        border_color=ft.colors.BLUE_300,
        focused_border_color=ft.colors.BLUE_600,
        text_style=ft.TextStyle(size=14),
    )
    
    password_field = ft.TextField(
        label="Password",
        width=350,
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.icons.LOCK,
        border_radius=15,
        filled=True,
        bgcolor=ft.colors.GREY_50,
        border_color=ft.colors.BLUE_300,
        focused_border_color=ft.colors.BLUE_600,
        text_style=ft.TextStyle(size=14),
    )
    
    error_text = ft.Text("", color=ft.colors.RED_400, size=12)
    
    def handle_login(e):
        username = username_field.value.strip()
        password = password_field.value.strip()
        
        if is_rate_limited(username):
            error_text.value = "⚠️ Too many attempts! Try again later."
            page.update()
            return
            
        if validate_login(username, password):
            show_dashboard_callback()
        else:
            error_text.value = "❌ Invalid username or password!"
            page.update()
    
    login_button = ft.ElevatedButton(
        "Sign In",
        icon=ft.icons.LOGIN,
        on_click=handle_login,
        width=350,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE_600,
            color=ft.colors.WHITE,
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
            shape=ft.RoundedRectangleBorder(radius=15),
        )
    )
    
    # Modern card-based login form
    login_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SHIELD_OUTLINED, size=60, color=ft.colors.BLUE_600),
                        ft.Text(
                            "Crime Analysis and Prediction System",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.BLUE_900,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Analysis Dashboard",
                            size=16,
                            color=ft.colors.GREY_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    margin=ft.margin.only(bottom=30)
                ),
                username_field,
                password_field,
                ft.Container(
                    content=login_button,
                    margin=ft.margin.only(top=20, bottom=10)
                ),
                error_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            padding=40,
            width=450,
        ),
        elevation=8,
        surface_tint_color=ft.colors.BLUE_50,
    )
    
    return ft.Container(
        content=login_card,
        alignment=ft.alignment.center,
        expand=True,
        gradient=ft.LinearGradient(
            colors=[ft.colors.BLUE_50, ft.colors.INDIGO_50, ft.colors.PURPLE_50],
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
        )
    )

# Modern Dashboard with Navigation Rail
def create_dashboard(page: ft.Page):
    # Navigation state
    selected_index = ft.Ref[int]()
    selected_index.current = 0
    
    # Content area
    content_area = ft.Ref[ft.Container]()
    
    def create_stats_tab():
        image_folder = "images/"
        stats_images = [
            image_folder + "Assault_crimes_in_Toronto.png",
            image_folder + "Crime_Indicator.png",
            image_folder + "Crime_Types_by_Hour_of_Day_in_Toronto.png",
            image_folder + "Elbow_Method_For_Optimal_k_2015.png",
            image_folder + "Major_Crime_Indicators_by_Month.png",
            image_folder + "Number_of_Major_Crimes_Reported_in_Toronto_in_2015.png",
        ]
        
        # Create modern image cards
        image_cards = []
        for i, img in enumerate(stats_images):
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Image(
                            src=img,
                            width=320,
                            height=240,
                            fit=ft.ImageFit.COVER,
                            border_radius=ft.border_radius.all(10)
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"Crime Analysis {i+1}",
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=ft.colors.GREY_700
                            ),
                            padding=ft.padding.only(top=10)
                        )
                    ]),
                    padding=15,
                ),
                elevation=3,
                surface_tint_color=ft.colors.GREY_50,
            )
            image_cards.append(card)
        
        # Arrange in grid
        grid_rows = []
        for i in range(0, len(image_cards), 3):
            row_cards = image_cards[i:i+3]
            grid_rows.append(
                ft.Row(
                    row_cards,
                    alignment=ft.MainAxisAlignment.START,
                    spacing=20
                )
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.ANALYTICS, size=28, color=ft.colors.BLUE_600),
                        ft.Text(
                            "Crime Statistics & Analytics",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.BLUE_900
                        )
                    ], spacing=10),
                    margin=ft.margin.only(bottom=30)
                ),
                *grid_rows
            ], spacing=20),
            padding=30
        )
    
    def create_predictive_tab():
        def open_crime_map(e):
            webbrowser.open("crime_map.html")
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.LOCATION_ON, size=28, color=ft.colors.RED_600),
                        ft.Text(
                            "Predictive Crime Hotspots",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.BLUE_900
                        )
                    ], spacing=10),
                    margin=ft.margin.only(bottom=30)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.MAP, size=60, color=ft.colors.RED_400),
                            ft.Text(
                                "Interactive Crime Map",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Text(
                                "View predicted crime hotspots based on historical data analysis",
                                size=14,
                                color=ft.colors.GREY_600,
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Container(
                                content=ft.ElevatedButton(
                                    "Open Crime Map",
                                    icon=ft.icons.OPEN_IN_NEW,
                                    on_click=open_crime_map,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.colors.RED_600,
                                        color=ft.colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    )
                                ),
                                margin=ft.margin.only(top=20)
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        padding=40,
                        width=400
                    ),
                    elevation=4
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30
        )
    
    def create_patrol_tab():
        police_station_lat = ft.TextField(
            label="Police Station Latitude",
            prefix_icon=ft.icons.LOCATION_ON,
            border_radius=10,
            filled=True,
            width=300
        )
        
        police_station_long = ft.TextField(
            label="Police Station Longitude",
            prefix_icon=ft.icons.LOCATION_ON,
            border_radius=10,
            filled=True,
            width=300
        )
        
        start_time = ft.TextField(
            label="Start Time (YYYY-MM-DD HH:MM:SS)",
            prefix_icon=ft.icons.ACCESS_TIME,
            border_radius=10,
            filled=True,
            width=300
        )
        
        end_time = ft.TextField(
            label="End Time (YYYY-MM-DD HH:MM:SS)",
            prefix_icon=ft.icons.ACCESS_TIME_FILLED,
            border_radius=10,
            filled=True,
            width=300
        )
        
        result_text = ft.Text("", size=14)
        progress_ring = ft.ProgressRing(visible=False)
        
        map_button = ft.ElevatedButton(
            "View Route on Map",
            icon=ft.icons.MAP,
            visible=False,
            on_click=lambda e: webbrowser.open("optimized_patrol_route.html"),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_600,
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10),
            )
        )
        
        def calculate_route(e):
            try:
                progress_ring.visible = True
                result_text.value = "Calculating optimal route..."
                result_text.color = ft.colors.BLUE_600
                page.update()
                
                generate_patrol_route_map(
                    float(police_station_lat.value),
                    float(police_station_long.value),
                    start_time.value,
                    end_time.value
                )
                
                progress_ring.visible = False
                result_text.value = "✅ Optimized route generated successfully!"
                result_text.color = ft.colors.GREEN_600
                map_button.visible = True
                
            except Exception as ex:
                progress_ring.visible = False
                result_text.value = f"❌ Error: {str(ex)}"
                result_text.color = ft.colors.RED_600
                map_button.visible = False
            
            page.update()
        
        calculate_button = ft.ElevatedButton(
            "Calculate Optimal Route",
            icon=ft.icons.ROUTE,
            on_click=calculate_route,
            width=250,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_600,
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10),
            )
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.ROUTE, size=28, color=ft.colors.GREEN_600),
                        ft.Text(
                            "Patrol Route Optimization",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.BLUE_900
                        )
                    ], spacing=10),
                    margin=ft.margin.only(bottom=30)
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Route Parameters",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.BLUE_800
                            ),
                            ft.Row([police_station_lat, police_station_long], spacing=20),
                            ft.Row([start_time, end_time], spacing=20),
                            ft.Container(
                                content=ft.Column([
                                    calculate_button,
                                    progress_ring,
                                    result_text,
                                    map_button
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                                margin=ft.margin.only(top=20)
                            )
                        ], spacing=20),
                        padding=30
                    ),
                    elevation=4
                )
            ]),
            padding=30
        )
    
    # Navigation change handler
    def on_nav_change(e):
        selected_index.current = e.control.selected_index
        
        if selected_index.current == 0:
            content_area.current.content = create_stats_tab()
        elif selected_index.current == 1:
            content_area.current.content = create_predictive_tab()
        elif selected_index.current == 2:
            content_area.current.content = create_patrol_tab()
        elif selected_index.current == 3:
            content_area.current.content = ft.Container(
                content=performance_tab,
                padding=30
            )
        
        page.update()
    
    nav_rail = ft.NavigationRail(
    selected_index=0,
    label_type=ft.NavigationRailLabelType.ALL,
    min_width=100,
    min_extended_width=200,
    bgcolor=ft.colors.BLUE_50,
    on_change=on_nav_change,
    expand=True,  # ← ADD THIS LINE
    destinations=[
        ft.NavigationRailDestination(
            icon_content=ft.Icon(ft.icons.ANALYTICS_OUTLINED),
            selected_icon_content=ft.Icon(ft.icons.ANALYTICS),
            label="Statistics",
        ),
        ft.NavigationRailDestination(
            icon_content=ft.Icon(ft.icons.MAP_OUTLINED),
            selected_icon_content=ft.Icon(ft.icons.MAP),
            label="Predictive Map",
        ),
        ft.NavigationRailDestination(
            icon_content=ft.Icon(ft.icons.ROUTE_OUTLINED),
            selected_icon_content=ft.Icon(ft.icons.ROUTE),
            label="Patrol Route",
        ),
        ft.NavigationRailDestination(
            icon_content=ft.Icon(ft.icons.SPEED_OUTLINED),
            selected_icon_content=ft.Icon(ft.icons.SPEED),
            label="Performance",
        ),
    ],
)
    
    # Initialize content area
    content_area.current = ft.Container(
        content=create_stats_tab(),
        expand=True,
        bgcolor=ft.colors.GREY_50
    )
    
    # Main layout
    return ft.Row([
    nav_rail,
    ft.Container(width=1, bgcolor=ft.colors.GREY_300),  # Divider
    content_area.current,
], expand=True, height=800)  

# Main app
def main(page: ft.Page):
    page.title = "Crime Analysis and Prediction System"
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 800
    page.window_min_height = 600
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    
    # Apply modern theme
    apply_modern_theme(page)
    
    def show_dashboard():
        page.clean()
        
        # Modern App Bar
        app_bar = ft.AppBar(
            title=ft.Row([
                ft.Icon(ft.icons.SHIELD, size=24, color=ft.colors.WHITE),
                ft.Text(
                    "Crine Analysis and Prediction Dashboard",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.WHITE
                )
            ], spacing=10),
            bgcolor=ft.colors.BLUE_700,
            actions=[
                ft.IconButton(
                    icon=ft.icons.SETTINGS,
                    icon_color=ft.colors.WHITE,
                    tooltip="Settings"
                ),
                ft.IconButton(
                    icon=ft.icons.LOGOUT,
                    icon_color=ft.colors.WHITE,
                    tooltip="Logout",
                    on_click=lambda e: main(page)  # Return to login
                ),
            ],
        )
        
        page.appbar = app_bar
        page.add(create_dashboard(page))
        page.update()
    
    # Show login page initially
    login_page = create_login_page(page, show_dashboard)
    page.add(login_page)

# Cleanup function
atexit.register(lambda: None)

# Run the app
if __name__ == "__main__":
    ft.app(target=main)
