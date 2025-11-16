import seaborn as sns
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from filterToDF import filteredDF

sns.set_theme()

@st.cache_data
def generateSankey(input_df, input_transport, input_day, input_timeSlot):
    # Filter input_df to get only rows matching input_transport, input_day, input_timeSlot
    df_sankey = filteredDF(input_df, input_transport, input_day, input_timeSlot, True)
    
    # If no data from input_df after filters applied return message and stop rendering process
    if df_sankey.empty:
        st.warning("⚠️ No data available for the selected filters.")
        return
    
    # Assign "_Start" or "_End" to Starting and ending towns of journeys
    for i in range(len(df_sankey)):
        if i == 0:
            df_sankey.at[i, "StartingTown"] = df_sankey.at[i, "StartingTown"] + "_Start"
            continue
        prev = df_sankey.iloc[i - 1]
        curr = df_sankey.iloc[i]
        if prev["journey_id"] != curr["journey_id"]:
            df_sankey.at[i - 1, "EndingTown"] = df_sankey.at[i - 1, "EndingTown"] + "_End"
            df_sankey.at[i, "StartingTown"] = df_sankey.at[i, "StartingTown"] + "_Start"
    
    # Mark the last row as the end of a journey
    df_sankey.at[len(df_sankey) - 1, "EndingTown"] = df_sankey.at[len(df_sankey) - 1, "EndingTown"] + "_End"
    
    # ===============================
    # Journey Legs with Number(count)
    # ===============================
    # Extract journey legs
    legs = df_sankey[['journey_id', 'StartingTown', 'EndingTown', 'mean_of_transport']].copy()
    # Count leg frequency (Sankey legs width)
    leg_counts = legs.groupby(['StartingTown', 'EndingTown', 'mean_of_transport']).size().reset_index(name='count')
    # Take top 20 legs
    top_legs = leg_counts.sort_values('count', ascending=False).head(20)
    
    # ==========================
    # Sankey Diagram
    # ==========================
    # Get list of all unique towns
    towns = pd.unique(top_legs[['StartingTown', 'EndingTown']].values.ravel())
    town_to_idx = {town: i for i, town in enumerate(towns)}
    # Map plain town names into ids (needed for sankey)
    sources = top_legs['StartingTown'].map(town_to_idx)
    targets = top_legs['EndingTown'].map(town_to_idx)
    
    # Display labels by removing "_Start" and "_End" suffixes 
    display_labels = [town.replace("_Start", "").replace("_End", "") for town in towns]
    # values = top_legs['duration_min']
    values = top_legs['count']
    
    # Assign colors to transport modes
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
    
    colors = [transport_colors.get(mode, "lightgray") for mode in top_legs['mean_of_transport']]
    
    # Plot Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=display_labels # clean labels without suffixes
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors,
            line=dict(color='black', width=0.5), # Black border for links
            hovertemplate='%{source.label} → %{target.label}: %{value:.0f}<extra></extra>'
        )
    )])
    
    # Create manual legend using Scatter (since Sankey doesn't support link legend directly)
    legend_items = []
    for mode, color in transport_colors.items():
        legend_items.append(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=15, color=color),
            legendgroup=mode,
            showlegend=True,
            name=mode
        ))
    
    # Add dummy traces to serve as the legend
    for trace in legend_items:
        fig.add_trace(trace)
    
    # Layout
    fig.update_layout(
        font_size=11,
        height=800,
        width=1100,
        margin=dict(l=40, r=20, t=50, b=40),
        # Hide all axes/scales on sides (no ticks, lines, grids, or labels)
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False, visible=False),
        legend=dict(
            x=1.02,  # displace legend (0.9 closer, 1.02 farther)
            y=1,
            traceorder='normal',
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='black',
            borderwidth=0.5
        )
    )
    # Town label color, arrow hover text size, town label size and no shadow
    fig.update_traces(textfont_color='black', link_hoverlabel_font_size=14, textfont_size=14, textfont_shadow=0, selector=dict(type='sankey'))
    
    st.plotly_chart(fig)    
