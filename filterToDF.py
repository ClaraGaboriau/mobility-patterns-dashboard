import pandas as pd
from datetime import time

def filteredDF(input_df, input_transport, input_day, input_timeSlot, removeLoops) :
    
    # ======================================================================================
    # Filter input_df to get only rows matching input_transport, input_day, input_timeSlot
    # ======================================================================================
        
    # Ensure inputs are always lists (for transport and day)
    if isinstance(input_transport, str):  # Check if input_transport is a single string
        input_transport = [input_transport]  # Convert it to a list with that single item
    if isinstance(input_day, str):  # Check if input_day is a single string
        input_day = [input_day]  # Convert it to a list with that single item
    
    
    start_slot, end_slot = input_timeSlot
    if not isinstance(start_slot, time) or not isinstance(end_slot, time):  # Validate that both are datetime.time objects
        raise ValueError("input_timeSlot must evaluate to a tuple of two datetime.time objects")
    
    if removeLoops == True :
        # Removes same_town trips      
        input_df = input_df[input_df['StartingTown'] != input_df['EndingTown']]
    
    # Ensure start_time and end_time are datetime
    input_df['start_time'] = pd.to_datetime(input_df['start_time'])  
    input_df['end_time'] = pd.to_datetime(input_df['end_time'])  
    
    # Extract only time component
    input_df['start_time_only'] = input_df['start_time'].dt.time
    input_df['end_time_only'] = input_df['end_time'].dt.time
    
    # Time slot filter
    time_filter = (
        (input_df['start_time_only'] >= start_slot) &
        (input_df['start_time_only'] < end_slot) &
        (input_df['end_time_only'] > start_slot) &
        (input_df['end_time_only'] <= end_slot)
    )
    
    filtered_df = input_df[  # Create a new filtered DataFrame
        input_df["mean_of_transport"].isin(input_transport) &  # Rows where mean_of_transport is in the input_transport list
        input_df["day_start"].isin(input_day) &  # Rows where day_start is in the input_day list
        time_filter  # Rows where the time filter condition is True
    ].reset_index(drop=True) 
    
    # Drop the now useless columns
    filtered_df = filtered_df.drop(columns=['start_time_only', 'end_time_only'], errors='ignore')  
    
    return filtered_df