import streamlit as st 


# ====================================================================
#           Mean distance done in km per type of transportation 
# ====================================================================

def generateDataFrame (input_df) : 
    
    input_df = input_df[input_df["mean_of_transport"] != "Plane"]    

    # Add together means of transportation and mean distances (km)
    df_grouped = (
        input_df.groupby("mean_of_transport", as_index=False)["distance_km"]
        .mean()
        .rename(columns={"mean_of_transport": "Transportation", "distance_km": "Mean distance (km)"})
    )
    
    df_grouped["Mean distance (km)"] = df_grouped["Mean distance (km)"].round(0).astype('Int64')
    
    st.dataframe(df_grouped,
                 column_order=("Transportation", "Mean distance (km)"),
                 hide_index=True,
                 use_container_width=True,
                 column_config={
                    "Transportation": st.column_config.TextColumn(
                        "Transportation",
                    ),
                    "Mean distance (km)": st.column_config.ProgressColumn(
                        "Mean distance (km)",
                        format="%d",
                        min_value=0,
                        max_value=int(df_grouped["Mean distance (km)"].max()),
                     )}
                 )



