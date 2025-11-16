import pandas as pd
from geopy.geocoders import Nominatim
from citiesNamesFromGeohash import getCitiesNames
from typing import Dict, Tuple
import streamlit as st


@st.cache_data
def load_cleaned_data() -> pd.DataFrame:
    # Load movememts data
    df_movement_data = pd.read_csv('data/all_movements.csv', sep=";")  

    # Use the function in citiesNamesFromGeohash
    df = getCitiesNames(df_movement_data)

    # Filter valid towns
    df = df[
        df["StartingTown"].notna() &
        df["EndingTown"].notna() &
        (df["StartingTown"].str.strip() != "") &
        (df["EndingTown"].str.strip() != "")
    ]

    # Preping time and date, sorting and converting into right format
    df = df.sort_values(by=["participant_id", "start_time"]).reset_index(drop=True)    
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df['start_date'] = df['start_time'].dt.date
    df['end_date'] = df['end_time'].dt.date
    
    # Compute duration
    df['duration'] = df['end_time'] - df['start_time'] 

    # Filter impossible intra-town trips (same town but huge distance or huge duration)
    MAX_INTRA_TOWN_KM = 30.0  # max distance in km for local trips
    MAX_INTRA_TOWN_HOURS = 2.0  # Max duration in hours for local trips
    
    # Convert dist in km and duration to hours
    df['distance_km'] = df['distance(m)'] / 1000
    df['duration_hours'] = df['duration'].dt.total_seconds() / 3600
    
    # Same town mask
    same_town = df["StartingTown"] == df["EndingTown"]
    # Drop if same town AND (dist too far OR duration too long)
    df = df[~(same_town & ((df['distance_km'] > MAX_INTRA_TOWN_KM) | (df['duration_hours'] > MAX_INTRA_TOWN_HOURS)))]

    
    # Keep in df only rows without transportation detection errors and without motorbikes
    df = df[~df['mean_of_transport'].isin(['DETECTION_ERROR', 'MOTORBIKE'])]

    # Get only what we are going to use (drop useless)
    df = df.drop(columns=["original_mean_of_transport", "gCO2", "is_power_saving", "distance(m)"])

    #======================================================
    #======================================================
    
    
    
    #======================================================
    # Filter distace(m) and duration outliers using speed
    #======================================================

    # Remove invalid rows (zero/negative distance or duration)
    df_clean = df[(df['distance_km'] > 0) & (df['duration'] > pd.Timedelta(0))].copy()

    # Calculate speed in km/h
    df_clean['speed_kmh'] = df_clean['distance_km'] / df_clean['duration_hours']

    # Define logical speed ranges (km/h) for each transport type
    speed_ranges : Dict[str, Tuple[float,float]] = {
        'WALKING': (1, 15),          # 1-15 km/h 
        'ON_BICYCLE': (5, 30),       # 5-30 km/h
        'ELECTRIC_BIKE': (10, 45),   # 10-45 km/h
        'SCOOTER': (5, 30),          # 5-30 km/h
        'CAR': (10, 250),            # 10-250 km/h
        'ELECTRIC_CAR': (10, 250),   # 10-250 km/h
        'HYBRID_CAR': (10, 250),     # 10-250 km/h
        'BUS': (10, 100),             # 10-100 km/h
        'ELECTRIC_BUS': (10, 100),    # 10-100 km/h
        'COACH': (20, 100),          # 20-100 km/h
        'TRAIN': (20, 300),          # 20-300 km/h
        'TRAM': (10, 60),            # 10-60 km/h
        'BOAT': (5, 50),             # 5-50 km/h
        'BOAT_NO_ENGINE': (2, 15),   # 2-15 km/h
        'PLANE': (200, 900),         # 200-900 km/h
        'ELECTRIC_SCOOTER': (5,30)   # 5-30 km/h
    }

    # Filter rows where speed is within the logical range for the transport type
    df_clean['valid_speed'] = df_clean.apply(
        lambda row: speed_ranges.get(row['mean_of_transport'], (float('-inf'), float('inf')))[0] <= row['speed_kmh'] <= speed_ranges.get(row['mean_of_transport'], (float('-inf'), float('inf')))[1], axis=1
    )
    df_filtered = df_clean[df_clean['valid_speed']].drop(columns=['duration_hours', 'speed_kmh', 'valid_speed']).reset_index(drop=True)

    #======================================================
    # Drop rows if overlapping legs from same participant
    #======================================================

    # Sort globally to ensure groups are consecutive
    df_filtered = df_filtered.sort_values(by=["participant_id", "start_time"]).reset_index(drop=True)

    # Mask to mark rows to drop
    to_drop = set()
    grouped = df_filtered.groupby('participant_id', group_keys=False)
    for _, group in grouped:
        # Preserve original global indices
        original_indices = group.index.tolist()
        group = group.sort_values('start_time').reset_index(drop=True)
    
        for i in range(len(group) - 1):
            if i >= len(to_drop.intersection(original_indices)):  # Skip if already marked
                continue
            row_i = group.iloc[i]
            row_j = group.iloc[i + 1]
            # Check for time overlap
            if (row_i['start_time'] < row_j['end_time']) and (row_j['start_time'] < row_i['end_time']):
                # Drop the shorter one; map back to global index
                if row_i['duration'] >= row_j['duration']:
                    to_drop.add(original_indices[i + 1])
                else:
                    to_drop.add(original_indices[i])

    # Apply drops
    df_cleaned = df_filtered.drop(to_drop, errors='ignore').reset_index(drop=True)

    #==================================================
    #==================================================

    # Add day of the week
    df_cleaned["day_start"] = df_cleaned["start_time"].dt.strftime('%A')

    #=======================================
    # Adding journey ids to legs
    #=======================================

    # Max allowed time gap to be considered a continuation
    MAX_TIME_GAP = 60

    # Create a list of ids for journey so that we can group legs with the same journey id
    journey_ids = []
    current_id = 0
    for i in range(len(df_cleaned)):
        if i == 0:
            journey_ids.append(current_id)
            continue
        prev = df_cleaned.iloc[i - 1]
        curr = df_cleaned.iloc[i]
        
        same_town = prev['EndingTown'] == curr['StartingTown']
        same_participant = prev['participant_id'] == curr['participant_id']
        same_day = prev['start_date'] == curr['start_date']
        time_diff = (curr['start_time'] - prev['end_time']).total_seconds() / 60
        
        if same_participant and same_day and (0 <= time_diff <= MAX_TIME_GAP) and same_town:
            journey_ids.append(current_id)
        else:
            current_id += 1
            journey_ids.append(current_id)

    df_cleaned['journey_id'] = journey_ids

    #====================================================
    # Renaming of mean_of_transport
    #====================================================
    transport_name_mapping = {
        'BOAT': 'Boat',
        'BOAT_NO_ENGINE': 'Boat',
        'BUS': 'Bus',
        'CAR': 'Car',
        'COACH': 'Bus',
        'ELECTRIC_BIKE': 'Bicycle',
        'ELECTRIC_BUS': 'Bus',
        'ELECTRIC_CAR': 'Car',
        'HYBRID_CAR': 'Car',
        'ON_BICYCLE': 'Bicycle',
        'PLANE': 'Plane',
        'SCOOTER': 'Scooter',
        'TRAIN': 'Train',
        'TRAM': 'Tram',
        'WALKING': 'Walking',
        'ELECTRIC_SCOOTER': 'Scooter'
    }
    df_cleaned['mean_of_transport'] = df_cleaned['mean_of_transport'].replace(transport_name_mapping)

    return df_cleaned
