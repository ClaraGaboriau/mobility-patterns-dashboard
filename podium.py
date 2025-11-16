import streamlit as st
import pandas as pd
import altair as alt
import pandas as pd

def show_podium(top3_df):
    
    top3_df["value_str"] = top3_df["value"].astype(str)
    
    # Fixed podium layout [1st, 2nd, 3rd]
    slots   = ["center", "left", "right"]     # bars
    heights = [3, 2, 1]                       # fixed bar heights
    emojis  = ["🥇", "🥈", "🥉"]

    top3_df["slot"]   = slots[:len(top3_df)]
    top3_df["height"] = heights[:len(top3_df)]
    top3_df["emoji"]  = emojis[:len(top3_df)]
    top3_df["y_mid"]  = top3_df["height"] / 2.0         # for emoji position
    top3_df["below_y"] = -0.25                     # small space below bars for duration text

    slot_order = ["left", "center", "right"]
    y_scale = alt.Scale(domain=[-0.4, max(top3_df["height"].max(), 3) + 0.5]) # bars height

    # White bars with black border
    bars = alt.Chart(top3_df).mark_bar(
        fill="#E1E8FB",
        stroke="black",
        strokeWidth=2,
        cornerRadiusTopLeft=6,  # chamfer
        cornerRadiusTopRight=6, # chamfer
        tooltip=None
    ).encode(
        x=alt.X("slot:N", sort=slot_order, axis=None, scale=alt.Scale(paddingInner=0, paddingOuter=0)),
        y=alt.Y("height:Q", axis=None, scale=y_scale)
    )

    # Emoji on the bars
    emojis_layer = alt.Chart(top3_df).mark_text(
        baseline="middle",
        fontSize=30,
        tooltip=None
    ).encode(
        x=alt.X("slot:N", sort=slot_order),
        y=alt.Y("y_mid:Q", scale=y_scale),
        text="emoji:N"
    )

    # Transport name on top of each bar
    names = alt.Chart(top3_df).mark_text(
        dy=-15, # distance transport mode title and bar
        fontSize=14,
        fontWeight="bold",
        tooltip=None
    ).encode(
        x=alt.X("slot:N", sort=slot_order),
        y=alt.Y("height:Q", scale=y_scale),
        text="mean_of_transport:N",
    )

    # Duration string below each bar (uses a small negative to create space)
    durations = alt.Chart(top3_df).mark_text(
        fontSize=12,
        tooltip=None
    ).encode(
        x=alt.X("slot:N", sort=slot_order),
        y=alt.Y("below_y:Q", scale=y_scale),
        text="value_str:N",
    )

    chart = (
        (bars + emojis_layer + names + durations)
        .properties(width=alt.Step(100), height=180)  
        .configure(background="transparent")
        .configure_view(fill="transparent", strokeWidth=0)
        .configure_scale(bandPaddingInner=0, bandPaddingOuter=0)  
        .configure_mark(tooltip=None)
    )

    st.altair_chart(chart, use_container_width=False)
    
    
def top3_duration(input_df) :
    
    # Parse datetimes (your strings already have timezone info like +00:00)
    input_df['start_time'] = pd.to_datetime(input_df['start_time'], utc=True, errors='coerce')
    input_df['end_time']   = pd.to_datetime(input_df['end_time'],   utc=True, errors='coerce')

    # Compute duration per row
    input_df['duration'] = input_df['end_time'] - input_df['start_time']
    
    # Sum durations by transport
    totals = (
        input_df.groupby('mean_of_transport', as_index=False)['duration']
        .sum()
        .sort_values('duration', ascending=False)
    )
    
    # Take top 3 by duration
    top_transport = totals.sort_values('duration', ascending=False).head(3)
    
    top_transport = top_transport.rename(columns={'duration': 'value',})
    show_podium(top_transport)



def top3_distance(input_df) :
    
    
    # Sum distances by transport
    totals = (
        input_df.groupby('mean_of_transport', as_index=False)['distance_km']
        .sum()
        .sort_values('distance_km', ascending=False)
    )
    
    totals['distance_km'] = totals['distance_km'].round(0).astype('Int64')
    
    # Take top 3 by distance
    top_transport = totals.sort_values('distance_km', ascending=False).head(3)
    
    top_transport['distance_km'] = top_transport['distance_km'].astype(str) + ' Km' 
    top_transport = top_transport.rename(columns={'distance_km': 'value',})
    show_podium(top_transport)


def top3_frequency(input_df) :
    
    # counts rows per mean of transport
    counts = (input_df['mean_of_transport']
          .value_counts()                 
          .rename_axis('mean_of_transport')
          .reset_index(name='counts')
    )
    
    # Take top 3 by counts
    top_transport = counts.sort_values('counts', ascending=False).head(3)
    
    top_transport['counts'] = top_transport['counts'].astype(str) + ' times'
    
    top_transport = top_transport.rename(columns={'counts': 'value',})
    show_podium(top_transport)


# Main method 
def generatePodium (input_df) :
    
    options = ["Duration", "Distance", "Frequency"]
    selection = st.pills("Select criteria :  ", options, selection_mode="single", default="Duration")
    
    if selection == "Duration" :
        top3_duration(input_df)
    elif selection == "Distance" :
        top3_distance(input_df)
    else : 
        top3_frequency(input_df)
