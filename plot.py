import altair as alt
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta

# Color assigning to transports
transport_colors = {
    "Bicycle": "#aec7e8",
    "Boat": "#8c564b",
    "Bus": "#d62728", 
    "Car": "#ff7f0e", 
    "Scooter": "#ff9896", 
    "Train": "#7ac07a",  
    "Tram": "#c5b0d5", 
    "Walking": "#1f77b4"   
}  


# Define days order for consistent plotting
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# ====================================================================
# Mean time stayed in transportation per days
# without plane, boat and detection error
# ====================================================================

@st.cache_data
def compute_time_data(input_df, input_town):
    if input_town is not None:
        # Only trips in the same city
        input_df = input_df[input_df['StartingTown'] == input_df['EndingTown']]
        # Only trips from the selected city
        input_df = input_df[input_df['StartingTown'] == input_town]
    
    if input_df.empty:
        st.warning("⚠️ This town doesn't have any trips inside it")
        return
    
    # Filter out 'PLANE' from CSV since too big/not that much used/useless
    input_df = input_df[input_df['mean_of_transport'] != 'Plane']  
    
    # Compute duration
    durations = []
    for i in range(len(input_df)):
        start = input_df['start_time'].iloc[i].time()
        end = input_df['end_time'].iloc[i].time()
        dt_start = datetime.combine(date.today(), start)
        dt_end = datetime.combine(date.today(), end)
        if dt_end < dt_start:
            dt_end += timedelta(days=1)
        durations.append(dt_end - dt_start)
    input_df['duration'] = durations
        
    # Group by day of week and mean of transport and mean duration
    df_grouped = input_df.groupby(['day_start', 'mean_of_transport'])['duration'].mean().reset_index()    
        
    # Convert duration to hours for plotting (time to decimal) ex: 5min20sec -> 0.0889 hours
    df_grouped['duration_hours'] = df_grouped['duration'].apply(lambda x: x.total_seconds() / 3600)  
    
    # Create complete index to fill missing combinations with zero
    transport_modes = list(transport_colors.keys())
    all_combinations = pd.MultiIndex.from_product([days_order, transport_modes], names=['day_start', 'mean_of_transport'])
    df_complete = pd.DataFrame(index=all_combinations).reset_index()
    df_grouped = df_complete.merge(df_grouped, on=['day_start', 'mean_of_transport'], how='left').fillna({'duration_hours': 0})
        
    # Format duration to hour/min/sec
    def format_duration(hours):
        if hours == 0:
            return "less than a min"
        if 0 < hours <= 1/60: # 1 minute = 1/60 hours
            return "less than a min"
        total_seconds = int(hours * 3600)
        hours_int = total_seconds // 3600
        total_seconds %= 3600
        mins = total_seconds // 60
        return f"{hours_int}h{mins}m" if hours_int > 0 else f"{mins}m"
    
    df_grouped['duration_formatted'] = df_grouped['duration_hours'].apply(format_duration)
    
    # Order days of week
    df_grouped['day_start'] = pd.Categorical(df_grouped['day_start'], categories=days_order, ordered=True)
    
    return df_grouped    

def compute_distance_data(input_df, input_town):
    
    if input_town is not None:
        # Only trips in the same city
        input_df = input_df[input_df['StartingTown'] == input_df['EndingTown']]
        
        # Only trips from the selected city
        input_df = input_df[input_df['StartingTown'] == input_town]
    
    if input_df.empty:
        return None
    
    # Filter out PLANE
    df_filtered = input_df[~input_df['mean_of_transport'].isin(['Plane'])].copy()
    
    # Compute mean distance (km) per day and transport
    df_grouped = (
        df_filtered
        .groupby(['day_start', 'mean_of_transport'], as_index=False)['distance_km']
        .mean()
    )
    
    # Create complete index to fill missing combinations with zero
    transport_modes = list(transport_colors.keys())
    all_combinations = pd.MultiIndex.from_product([days_order, transport_modes], names=['day_start', 'mean_of_transport'])
    df_complete = pd.DataFrame(index=all_combinations).reset_index()
    df_grouped = df_complete.merge(df_grouped, on=['day_start', 'mean_of_transport'], how='left').fillna({'distance_km': 0})
    
    # Round numbers (nearest km) for display
    df_grouped['distance_km_rounded'] = df_grouped['distance_km'].apply(
        lambda x: "less than 1" if 0 < x <= 1 else str(int(round(x)))
    )
    
    # Order days of week
    df_grouped['day_start'] = pd.Categorical(df_grouped['day_start'], categories=days_order, ordered=True)
    
    return df_grouped       
       
# Main method using cached computation functions and handle empty data
def generatePlot(input_df, input_town, input_selection):
    
    if input_selection == "time":
        df_grouped = compute_time_data(input_df, input_town)
        if df_grouped is None:
            st.warning("⚠️ This town doesn't have any trips inside it")
            return
        # Create Altair chart
        chart = alt.Chart(df_grouped).mark_bar().encode(
            x=alt.X('duration_hours:Q', title='Total Mean Time Spent (Hours)',
                    axis=alt.Axis(tickMinStep=1, format='.0f', tickCount=2)),
            y=alt.Y('day_start:N', title='Day of the Week', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
            color=alt.Color('mean_of_transport:N',
                            title='Transport Mode',
                            scale=alt.Scale(
                                domain=list(transport_colors.keys()),
                                range=list(transport_colors.values())
                            )),
            tooltip=[
                alt.Tooltip('mean_of_transport:N', title='Transport'),
                alt.Tooltip('duration_formatted:N', title='Mean Duration')
            ]
        ).configure(background="transparent").properties(
            width=700,
            height=400
        )
        
    else:  # Selection is distance
        df_grouped = compute_distance_data(input_df, input_town)
        if df_grouped is None:
            st.warning("⚠️ This town doesn't have any trips inside it")
            return
        
        # Create Altair chart
        chart = alt.Chart(df_grouped).mark_bar().encode(
            x=alt.X('distance_km:Q', title='Total Mean Distance (km)',
                    axis=alt.Axis(tickMinStep=1, format='.0f', tickCount=2)),
            y=alt.Y('day_start:N', title='Day of the Week', sort=days_order),
            color=alt.Color('mean_of_transport:N',
                            title='Transport Mode',
                            scale=alt.Scale(
                                domain=list(transport_colors.keys()),
                                range=list(transport_colors.values())
                            )),
            tooltip=[
                alt.Tooltip('mean_of_transport:N', title='Transport'),
                alt.Tooltip('distance_km_rounded:N', title='Mean Distance (km)')
            ]
        ).configure(background="transparent").properties(
            width=700,
            height=400
        )
    # Show in Streamlit
    st.altair_chart(chart, use_container_width=True)      
