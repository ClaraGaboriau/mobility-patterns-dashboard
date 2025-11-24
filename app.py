import streamlit as st
import pandas as pd
import base64
from data import load_cleaned_data
from sankey import generateSankey
from arcLayer import generateArcLayer
from heatmapArray import heatmapArray
from plot import generatePlot
from podium import generatePodium
from datetime import time
from pieChart import generateChart
from dataframeMain import generateDataFrame


# Load and encode the local SVG icon
with open("filterIcon.svg", "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode()
FILTER_ICON = f"data:image/svg+xml;base64,{encoded_string}"


st.set_page_config(
    page_title="Data mouvement dashboard",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded")

#######################
# Load data
df = load_cleaned_data()
# df.to_csv("full_dataframe.csv", index=False) # Testing purpose

#######################
# Sidebar
with st.sidebar:
    st.title("Data mouvement dashboard filters")
    
    # Types of transportation multiselect
    transport_types = df['mean_of_transport'].dropna().unique()
    transport_streamlit_multiselect = st.multiselect(
    "Type of transportation :",
    transport_types,
    default=["Walking","Train"],
    )
    
    # Days of week multiselect
    day_streamlit_multiselect = st.multiselect(
    "Day of week :",
    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    default=["Monday"],
    )
    
    # Time slots slider 
    time_slot_streamlit_slider = st.slider(
        "Select time slot of the day :", value=(time(8, 0), time(12, 0))
    )
    
    st.write('''
                    The purpose of this application is to build with a mobility dataset an interactive 
                    visualizations of transportation means by individuals, as well as global presence 
                    in public space during typical days/towns. 
                ''')
    
#######################   
# Page title 

st.title("Visualization of global mobility patterns") 
    
    
#######################
# Dashboard Main Panel

tab1, tab2, tab3 = st.tabs(["Mobility overview", "Space usage analysis", "Transportation mode comparison"])

with tab1: # Mobility overview tab 
    with st.container() : 
        col = st.columns((5,1,2), gap='medium') 
    
        with col[0]:
        
            #======================================================
            #       Plot (information about mean time OR  spent in transportation
            #       Doesn't take into consideration filters (no need)) 
            #                           +
            #       HEATMAP (according to day and transportation from 
            #       user choices)
            #                           +
            #       Sankey (according to user choices) 
            #======================================================
        
            # Plot
            st.subheader("Mean time spent in transportation by day")
            generatePlot(df, None, "time") # df, no town, displaying mean time spent 
        
            # Array heatmap 
            st.divider()
            st.subheader("Number of persons in a town during time slots (top 20 towns)")
            st.markdown(f'''( <img src="{FILTER_ICON}" width="20" style="vertical-align: middle;"> : only day filtering)
                    ''', unsafe_allow_html=True)
            heatmapArray(df,day_streamlit_multiselect)
            
                
        with col[1]:
            st.empty()
    

        with col[2]: 
        
            #======================================================
            #               Podium for transportation
            #       (no filter needed) -> Total time spent
            #                          -> Total distance 
            #                          -> Total times used  
            #                       +
            #               Data Frame of km per transportation type
            #                       +
            #               About expander explaining app
            #======================================================
        
            # Podium
            generatePodium(df)
            
            # Data Frame 
            generateDataFrame(df)
            
            # About expander 
            with st.expander('About', expanded=True):
                st.markdown(f'''
                    - :blue[**Data**]: gathered through the Swice mobile app. The dataset represents each segment 
                        of a person’s mobility patterns.  

                    - :blue[**Filters**]: permits to select specific data. Not all graphs use filters. 
                        To know if filters are used, you will find a filter icon: <img src="{FILTER_ICON}" width="20" style="vertical-align: middle;">
                    ''', unsafe_allow_html=True)
                
            
        with st.container() : 
            
            # Sankey
            st.divider()
            st.subheader("Top 20 Most Common Journey Legs (Excluding Same-Town Trips)")
            st.markdown(f'''( <img src="{FILTER_ICON}" width="20" style="vertical-align: middle;"> : all filters)
                    ''', unsafe_allow_html=True)
            
            if not transport_streamlit_multiselect:
                st.warning("⚠️ Please select at least one transport type.")
            elif not day_streamlit_multiselect:
                st.warning("⚠️ Please select at least one day of the week.")
            else:
                fig = generateSankey(df, transport_streamlit_multiselect, day_streamlit_multiselect, time_slot_streamlit_slider)
                
    
with tab2: # Space usage analysis
    
    #============================================================================
    #                              Arc layer 
    #============================================================================
    
    st.subheader("Geographic visualization of inter-town mobility and intra-town activity")
    st.markdown(f'''( <img src="{FILTER_ICON}" width="20" style="vertical-align: middle;"> : all filters)
                    ''', unsafe_allow_html=True)

    generateArcLayer(df, transport_streamlit_multiselect, day_streamlit_multiselect, time_slot_streamlit_slider)
    

with tab3: #Transportation mode comparison
    st.subheader("Transportation data charts")
    col1, col2, col3 = st.columns((4,3,4), gap='small') 
    
    #============================================================================
    #              Select box of towns available after filters applied   
    #                 + Pie chart showing transportation usage in selected town 
    #                 + mini arc layers showing intra town trips
    #============================================================================
    list_df = df.copy()
    
    #df_filtered_list = filteredDF(list_df, transport_streamlit_multiselect, day_streamlit_multiselect, time_slot_streamlit_slider, False)
    
    # list of towns 
    df_only_inner_trips = df[df["StartingTown"] == df["EndingTown"]]
    df_list = pd.concat([df_only_inner_trips['StartingTown'], df_only_inner_trips['EndingTown']]).unique().tolist()
    df_list = sorted(df_list)

with col1:
    # Selectbox 
    option = st.selectbox(
        "Select city : ",
        df_list,
        key="city_selectbox_1"
    )
    
    # Pie chart 
    generateChart(df, option)
    
    # horizontal bar plot 
    st.divider()
    st.text("Mean time and distance spent in transportation by day in " + option)
    options = ["time", "distance"]
    selection = st.pills(
        "Select criteria :  ", options,
        selection_mode="single",
        default="time",
        key="criteria_pills_1"
    )
    generatePlot(df, option, selection)

with col2: 
    with st.container():
        # Nested column to center the toggle
        _, center_col, _ = st.columns([1, 2, 1])  # Adjust ratios for width
        with center_col:
            on = st.toggle("Activate comparison", key="compare_toggle")

with col3:
    # If compare toggle set to on 
    if on:
        option2 = st.selectbox(
            "Select city : ",
            df_list,
            key="city_selectbox_2"
        )
        # Pie chart
        generateChart(df, option2) 
        
        # horizontal bar plot 
        st.divider()
        st.text("Mean time and distance spent in transportation by day in " + option2)
        options2 = ["time", "distance"]
        selection2 = st.pills(
            "Select criteria :  ", options2,
            selection_mode="single",
            default="time",
            key="criteria_pills_2"
        )
        generatePlot(df, option2, selection2)
