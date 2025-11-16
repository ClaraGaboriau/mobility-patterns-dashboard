import pandas as pd
import numpy as np
import pydeck as pdk
import streamlit as st
import matplotlib.pyplot as plt
from geolib import geohash as geolib
from matplotlib import colormaps as cmaps
import pickle
from pathlib import Path
from datetime import time as datetime_time

# Geohashes to coordinates, from file if it exists, otherwise create it
try:
    with Path('geohashes_to_coords.pkl').open("rb") as f:
        geo_to_coords = pickle.load(f)
except:
    geo_to_coords = {}

# Get coordinates from geohashes
def geohash_to_coordinate(geohash):
    try:
        lat, lon = geolib.decode(geohash)
        return [float(lat), float(lon)]
    except:
        return [0.0, 0.0]

# Populate town dictionary
def geohashes_to_coordinate(geohashes):
    new_data = False
    for geohash in geohashes:
        # Populate coords dictionary
        if geohash not in geo_to_coords:
            geo_to_coords[geohash] = geohash_to_coordinate(geohash)
            new_data = True
    # Save both dictionaries
    if new_data:
        try:
            with open('geohashes_to_coords.pkl', 'wb') as f:
                pickle.dump(geo_to_coords, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            pass
    return geo_to_coords


# Define the colormap
@st.cache_resource
def set_colormap(cm_name='coolwarm'):
    base = cmaps[cm_name]
    # Define plasma color map
    plasma_colormap = [base(i)[:3] for i in range(256)]  # Get 256 RGB values
    plasma_colormap = [[int(r*255), int(g*255), int(b*255)] for r, g, b in plasma_colormap]  # Convert to 0-255
    return plasma_colormap


def generateHeatmap (input_transport, input_day, input_timeSlot, input_lat, input_long, input_town) :
    df_paths_data = pd.read_csv('data/all_paths.csv', sep=";")
    
    # Make input_day in capital letter for after use
    input_day = [d.upper() for d in input_day]
    
    # Make input_transport same as in the df_paths_data data frame to ensure filter compatibility
    transport_name_mapping = {
        'Boat': 'BOAT',
        'Bus': 'BUS',
        'Car': 'CAR',
        'Bicycle':'ON_BICYCLE',
        'Plane':'PLANE',
        'Train':'TRAIN',
        'Tram':'TRAM',
        'Walking':'WALKING'
    }
    input_transport = [transport_name_mapping.get(t, t) for t in input_transport] #returns the mapped value if it exists, otherwise keeps the original
    
    ## Filtering data 
    
    # Ensure inputs are always lists (for transport and day)
    if isinstance(input_transport, str):  # Check if input_transport is a single string
        input_transport = [input_transport]  # Convert it to a list with that single item
    if isinstance(input_day, str):  # same
        input_day = [input_day]  # same
        
    # Get first part of time range
    df_paths_data['hour'] = df_paths_data['time_range'].apply(lambda x: x.split('-')[0])
    df_paths_data['hour'] = df_paths_data['hour'].astype(int)
    
    # Get start and end slot time
    start_slot, end_slot = input_timeSlot
    if not isinstance(start_slot, datetime_time) or not isinstance(end_slot, datetime_time):# Validate that both are datetime.time objects
        raise ValueError("input_timeSlot must evaluate to a tuple of two datetime.time objects")
    # Extract hours from the datetime.time objects
    start_hour = start_slot.hour
    end_hour   = end_slot.hour

    # Filter rows whose hour is between start and end hour
    filtered_df = df_paths_data.loc[
        (df_paths_data['hour'] >= start_hour) &
        (df_paths_data['hour'] <= end_hour)
    ]       

    heatmap_df = filtered_df[  # Create a new filtered DataFrame
        filtered_df["mode_of_transport"].isin(input_transport) &  # Rows where mode_of_transport is in the input_transport list
        filtered_df["day_of_week"].isin(input_day)  # Rows where day_of_week is in the input_day list
    ].reset_index(drop=True) 
    
    # If no data from input_df after filters applied return message and stop rendering process
    if heatmap_df.empty:
        st.warning("⚠️ No data available for the selected filters.")
        return
    
    #========================
    
    
    # Group by geohash, hour and mode of transport, and count the number of occurrences -- faster for the viz later
    agg = heatmap_df.groupby(['geohash', 'hour', 'mode_of_transport'], sort=False).size().reset_index(name='count')

    # Collapse to per-geohash totals
    df = agg.groupby("geohash", as_index=False, sort=False)["count"].sum()

    # Populate the geohash to coordinates dictionary
    geo_to_coords = geohashes_to_coordinate(df['geohash'].astype(str).unique())

    # Transform geohashes to coordinates (fast path using array)
    coords_arr = np.array([geo_to_coords[g] for g in df["geohash"].astype(str).values], dtype=float)
    df["latitude"]  = coords_arr[:, 0]
    df["longitude"] = coords_arr[:, 1]
    
    # Set colormap
    colormap = set_colormap("coolwarm")

    # Create a Pydeck layer
    layer = pdk.Layer(
        'HeatmapLayer',
        df,
        get_position=['longitude', 'latitude'],
        get_weight='count',
        color_range=colormap,  # Apply selected colormap
        aggregation = 'SUM',
        opacity=1.0,
        pickable=False,
    )

    view_state = pdk.ViewState(
            latitude=input_lat,
            longitude=input_long,
            zoom=13,
            min_zoom=8,
            max_zoom=17,
        )

    st.pydeck_chart(
        pdk.Deck(
            layer,
            initial_view_state=view_state,
            map_style="light",
        ),
        use_container_width=True
    )
    
    