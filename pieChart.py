import matplotlib.pyplot as plt
import streamlit as st 


# Color assigning to transports using tableau20 palette
transport_colors = {
    "Bicycle": "#aec7e8",
    "Boat": "#8c564b",
    "Bus": "#d62728", 
    "Car": "#ff7f0e",
    "Plane": "#7B7B7B", 
    "Scooter": "#ff9896", 
    "Train": "#7ac07a",  
    "Tram": "#c5b0d5", 
    "Walking": "#1f77b4"   
} 

@st.cache_data
def compute_chart_data(input_df, town_name) : 
    
    df = input_df
    
    # Only trips in the same city
    df = df[df['StartingTown'] == df['EndingTown']]
    # Only trips from the selected city
    df = df[df['StartingTown'] == town_name]
    # Select only the specified columns
    df = df[['distance_km', 'mean_of_transport', 'StartingTown']]
    # Keeping "distance_km, mean_of_transport, StartingTown" 


    # Group by 'mean_of_transport' and count the occurrences
    counts = df['mean_of_transport'].value_counts()
    
    # Calculate percentages 
    percentages = (counts / counts.sum()) * 100

    # Show labels only if >2%
    labels = [label if pct > 2 else '' for label, pct in zip(counts.index, percentages)]
    
    # Colors
    color_list = [transport_colors.get(mode, "lightgray") for mode in counts.index]
    
    return {
        "counts": counts,
        "percentages": percentages,
        "labels": labels,
        "color_list": color_list
    }
    
def generateChart(input_df, town_name):    
    
    # Get cached chart data
    chart_data = compute_chart_data(input_df, town_name)
    
    # Check for empty data
    if chart_data["counts"].empty:
        st.warning(f"⚠️ No transportation data available for {town_name}.")
        return
    
    # Create figure and axis for the pie chart
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(
        chart_data["counts"],
        labels=chart_data["labels"],
        colors=chart_data["color_list"],
        autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',  # Show percentage inside slice only if >5%
        textprops={'fontsize': 15},
        labeldistance=1.2,  # Controls label distance from center
        startangle=90
    )
    # ax.set_title('Distribution of means of transportation in ' + town_name + ' (number of usages)', fontsize=20, pad=100)
    
    # Set figure-level suptitle to decouple from axes and prevent title length from affecting pie size
    fig.suptitle(
        f'Distribution of means of transportation in {town_name}\n(number of usages)',
        fontsize=20,
        y=0.95  # Fixed vertical position near top
    )
    ax.axis('equal')  # Equal aspect ratio ensures the pie is drawn as a circle
    fig.subplots_adjust(top=0.78)
    # Display
    st.pyplot(fig)