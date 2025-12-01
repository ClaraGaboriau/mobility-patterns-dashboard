import pandas as pd
import numpy as np
import streamlit as st
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="TB_py_app_claragaboriau", timeout=10)
import pydeck as pdk
from filterToDF import filteredDF
from heatmap import generateHeatmap
import matplotlib.pyplot as plt  # For Viridis colormap
from matplotlib.colors import LogNorm, Normalize  
import os  # Pickle cache file handling
import pickle  # Pickle cache

# For basemap
pdk.settings.mapbox_api_key = "pk.eyJ1IjoiY2xhcmFnYWJ6IiwiYSI6ImNtOXNjZWwwZjAxNmEybHFwMHA2bmlwZzkifQ.9rbBUmuSZFfucFDRJo9IYg"

@st.cache_data
# Method that does filtering, separating long and short trips, putting everything in the correct category
def compute_trip_and_town_data(input_df, input_transport, input_day, input_timeSlot):
    
    # Filter input_df to get only rows matching input_transport, input_day, input_timeSlot, no loops removed
    df_arcLayer = filteredDF(input_df, input_transport, input_day, input_timeSlot, False)
    
    # Get towns with inner trips
    inner_towns = set(df_arcLayer[df_arcLayer['StartingTown'] == df_arcLayer['EndingTown']]['StartingTown'].unique())
    
    # If no data from input_df after filters applied return message and stop rendering process
    if df_arcLayer.empty:
        return None
    
    
    # Collect all unique towns for batch geocoding
    unique_towns = pd.concat([df_arcLayer['StartingTown'], df_arcLayer['EndingTown']]).dropna().unique()
    # Load or initialize pickle cache for town -> (lat, long)
    cache_file = "town_to_coords_cache.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = {}
    
    # Define geocoding function to get lat long
    def get_lat_long(town):
        name = str(town).strip()
        
        if pd.isna(town) or not name:
            return None, None
        try:  # Wrap geocode call in try/except to catch timeouts/errors
            # Query Nominatim for locations matching the town name (multiple results possible)
            locations = geolocator.geocode(
                name,  # Cleaned town string
                exactly_one=False,  # Get all matches, not just the top one
                addressdetails=True,  # Include extra metadata like type/importance
            )
            if not locations:  # If no matches at all
                return None, None
            
            # Check if a location is "city-like" (ex: town, not a street or country or canton...)
            def is_city_like(loc):
                raw = loc.raw or {}  # get raw JSON from geopy result or empty dict
                # Extract keys + lowercased for matching
                type_val = raw.get("type", "").lower()  # ex: "city"
                class_val = raw.get("class", "").lower()  # ex: "place"
                addr_type = raw.get("addresstype", "").lower()  # if nothing worked
                # Match: must be "place" class with accepted type or addresstype matches
                return (class_val == "place" and type_val in ("city", "town", "municipality", "village")) or \
                       addr_type in ("city", "town", "municipality", "village")
            
            # Filter to city-like results only
            candidates = [loc for loc in locations if is_city_like(loc)] or locations
            
            # Pick the "best" one: Highest importance score (from Nominatim metadata)
            chosen = max(candidates, key=lambda l: float(l.raw.get("importance", 0)))  # Default 0 if missing
            
            # Return the lat/long tuple from the chosen location
            return chosen.latitude, chosen.longitude
        
        except:  
            return None, None
    
    
    # Cache missing towns (batch process uniques)
    for town in unique_towns:
        if town not in cache:
            cache[town] = get_lat_long(town)
    
    # Save updated cache to file
    with open(cache_file, "wb") as f:
        pickle.dump(cache, f)
    
    # Get unique directed pairs with counts -> arcs colored by occurrence frequency
    geo_info = df_arcLayer[['StartingTown', 'EndingTown']].value_counts().reset_index(name='count')
    
    # Exclude self-loops from arcs (inner trips information is available thanks to scatterplot)
    geo_info = geo_info[geo_info['StartingTown'] != geo_info['EndingTown']]
    
    # Build trip_data from counted pairs (one row per unique arc, with count)
    trip_data = geo_info.copy()
    
    # Assign coords using cache (if town doesn't exist, it defaults to (None, None))
    trip_data['startLat'] = trip_data['StartingTown'].map(lambda t: cache.get(t, (None, None))[0]) 
    trip_data['startLong'] = trip_data['StartingTown'].map(lambda t: cache.get(t, (None, None))[1]) 
    trip_data['endLat'] = trip_data['EndingTown'].map(lambda t: cache.get(t, (None, None))[0])
    trip_data['endLong'] = trip_data['EndingTown'].map(lambda t: cache.get(t, (None, None))[1])
    
    # Remove any rows where the geographic coordinates (lat/long for start and end points) are invalid
    valid_mask = ~(trip_data['startLat'].isna() | trip_data['startLong'].isna() | 
                   trip_data['endLat'].isna() | trip_data['endLong'].isna()) # True : no rows with missing lat/long
    trip_data = trip_data[valid_mask].reset_index(drop=True)
    
    # Column assignment for positions
    trip_data["source_position"] = trip_data[["startLong", "startLat"]].apply(
        lambda row: [row["startLong"], row["startLat"]], axis=1)
    trip_data["target_position"] = trip_data[["endLong", "endLat"]].apply(
        lambda row: [row["endLong"], row["endLat"]], axis=1)
    if trip_data.empty:
        return None
    
    # Populate random arc heights per trip (one unique float per row)
    if len(trip_data) > 0:
        trip_data['arc_height'] = np.random.uniform(0.4, 1.0, size=len(trip_data))
    
    trip_data = pd.read_json(trip_data.to_json())  # Ensure JSON-compatible
    
    # Map counts to Viridis colors using log scale
    if len(trip_data) > 0:
        min_count = trip_data['count'].min()
        max_count = trip_data['count'].max()
        if min_count == max_count:
            norm = Normalize(vmin=1, vmax=1)  # Fallback to single value
        else:
            norm = LogNorm(vmin=min_count, vmax=max_count)
        viridis_colors = plt.cm.viridis(norm(trip_data['count']))
        rgb_colors = (255 * viridis_colors[:, :3]).astype(int).tolist()  # Convert to list of [R,G,B] lists
        trip_data['source_color'] = rgb_colors
        trip_data['target_color'] = rgb_colors 
    
    # Tooltip text for the arc layers
    trip_data["tooltip_text"] = trip_data.apply(
    lambda row: f"<b>{row['StartingTown'].rsplit(', ', 1)[0]} → {row['EndingTown'].rsplit(', ', 1)[0]}</b><br>Occurrences: {row['count']}",
    axis=1
    )
    
    # Town_df: Only for inner towns (self-loops), using cache
    town_df_data = []
    for town in inner_towns:
        coords = cache.get(town, (None, None))
        if coords[0] is not None and coords[1] is not None: # lat long not None
            town_df_data.append({"town": town, "latitude": coords[0], "longitude": coords[1]})
    town_df = pd.DataFrame(town_df_data)
    if town_df.empty:
        return {
            "trip_data": trip_data,
            "town_df": None
        }
    town_df["tooltip_text"] = town_df["town"].apply(lambda t: f"<b>{t}</b>")
    return {
        "trip_data": trip_data,
        "town_df": town_df
    }

# Main method
def generateArcLayer(input_df, input_transport, input_day, input_timeSlot):
    
    # Call using caching
    computed = compute_trip_and_town_data(input_df, input_transport, input_day, input_timeSlot)
    
    # Handle None return from cached compute
    if computed is None:
        st.warning("⚠️ No data available for the selected filters.")
        return
    
    # Data from computed dict
    trip_data = computed["trip_data"]
    town_df = computed["town_df"]
    
    # Default Fribourg lat long
    Lat = 46.802502
    Long = 7.151280
    
    # Define initial view state (the broad starting view)
    initial_view_state = pdk.ViewState(
        latitude=Lat,
        longitude=Long,
        bearing=0,
        pitch=50,
        zoom=7,
    )
    # Initialize session_state for current view if not present (preserves user pans/zooms)
    if 'current_view_state' not in st.session_state:
        st.session_state.current_view_state = initial_view_state
    
    # Use current view state for the Deck
    view_state = st.session_state.current_view_state
    
    # Create scatterplot layer
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=town_df,
        id="towns_scatter",
        get_position=["longitude", "latitude"],
        get_fill_color=[144,238,144],  # light green
        get_line_color=[0, 0, 0, 255],  # black
        pickable=True,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=6,
        radius_max_pixels=12,
        line_width_min_pixels=1
    )
    # Create ArcLayers using Viridis-based coloring by count
    arc_layer = pdk.Layer(
        "ArcLayer",
        trip_data,
        id="arc_layer",
        get_source_position="source_position",
        get_target_position="target_position",
        get_source_color="source_color",  # Dynamic Viridis color by count
        get_target_color="target_color",  
        get_width=1,  
        pickable=True,
        auto_highlight=True,
        width_scale=0.1,
        width_min_pixels=3,
        opacity=0.8, 
        get_height="arc_height"
    )
    # Render view
    view_state = pdk.ViewState(
        latitude=float(Lat),
        longitude=float(Long),
        bearing=0,
        pitch=50,
        zoom=7,
    )
    deck = pdk.Deck(layers=[scatter_layer, arc_layer],
                    initial_view_state=view_state,
                    map_style="mapbox://styles/mapbox/streets-v12",
                    tooltip={
                        "html": "{tooltip_text}",
                        "style": {
                            "backgroundColor": "#6495ED",
                            "color": "white"
                        }
                    }
    )
    deck.mapbox_key = pdk.settings.mapbox_api_key
    # Event : on click, app will display heatmap of the clicked town
    event = st.pydeck_chart(deck,  # draws layers
                            on_select='rerun',  # rerun code from the top (mandatoty with streamlit)
                            selection_mode="single-object")  # only one click at a time
    if (
            event.selection is not None
            and hasattr(event.selection, "objects")
            and "towns_scatter" in event.selection.objects
    ):
        # Get clicked object
        selected_obj = event.selection.objects["towns_scatter"][0]  # single-object mode => first item
        sel_lat = selected_obj["latitude"]
        sel_lon = selected_obj["longitude"]
        apt_town_name = selected_obj["town"]
        st.session_state["selected_towns_scatter"] = {
            "town": apt_town_name,
        }
        # Heatmap call showing only short trips of the selected town + zoom on town
        st.divider()
        with st.container():
            st.write(f"**Selected town**: {st.session_state['selected_towns_scatter']['town']}")
            generateHeatmap(input_transport, input_day, input_timeSlot, sel_lat, sel_lon, apt_town_name)
    else:
        # Placeholder message
        st.info("Click a town point (green dot) to view its heatmap. Hover arcs for trip details.")
