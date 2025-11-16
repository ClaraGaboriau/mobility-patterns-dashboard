
import pandas as pd
from geopy.geocoders import Nominatim
from geolib import geohash
import streamlit as st 
import pickle 
import os 

def getCitiesNames(df: pd.DataFrame) -> pd.DataFrame:
    # Initialize Nominatim
    geolocator = Nominatim(user_agent="my_geopy_app", timeout=10)
    
    # ====================================================================
    # Create starting/ending town columns from start/end geohashes
    # ====================================================================
    # Load or initialize cache (key: geohash, value: "Town, CC")
    cache_file = "nominatim_cache.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = {}

    def geohashes_to_town_column(df, column_name, new_column_name):
        unique_geohashes = df[column_name].dropna().unique()
        for ghash in unique_geohashes:
            if ghash in cache:
                continue
            try:
                lat, lon = geohash.decode(ghash)
                location = geolocator.reverse((lat, lon))
                if location and location.raw.get('address'):
                    address = location.raw['address']
                    town = address.get('town') or address.get('city') or address.get('village') or ''
                    country_code = address.get('country_code', '').upper()  # e.g. 'CH'
                    
                    if not country_code:
                        print(f"WARNING: No country_code for geohash {ghash} at ({lat}, {lon}) - using bare town")
                        enriched_town = town
                    else:
                        enriched_town = f"{town}, {country_code}" if town else ''
                    
                    cache[ghash] = enriched_town
                else:
                    cache[ghash] = ''
                    print(f"No address for {ghash}")
            except Exception as e:
                print(f"Error with {ghash}: {e}")
                cache[ghash] = ''
        
        # Map enriched towns to DataFrame
        df[new_column_name] = df[column_name].map(cache)
    
    # Process start and end geohashes
    geohashes_to_town_column(df, 'start_geohash', 'StartingTown')
    geohashes_to_town_column(df, 'end_geohash', 'EndingTown')
    
    # Save updated cache
    with open(cache_file, "wb") as f:
        pickle.dump(cache, f)
    
    return df