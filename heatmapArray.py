import altair as alt
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time


# Define fixed slots (relative to a single day)
fixed_slots = [
    ("00h-06h", time(0, 0), time(6, 0)),
    ("06h-08h", time(6, 0), time(8, 0)),
    ("08h-10h", time(8, 0), time(10, 0)),
    ("10h-12h", time(10, 0), time(12, 0)),
    ("12h-14h", time(12, 0), time(14, 0)),
    ("14h-16h", time(14, 0), time(16, 0)),
    ("16h-18h", time(16, 0), time(18, 0)),
    ("18h-20h", time(18, 0), time(20, 0)),
    ("20h-22h", time(20, 0), time(22, 0)),
    ("22h-24h", time(22, 0), time(23, 59, 59)),
]

# Assign corresponding fixed slots
@st.cache_data
def getTimeSlot(inferred_df):
    slots = []
    for _, row in inferred_df.iterrows():
        from_time = pd.to_datetime(row["from_time"]).tz_localize(None)
        to_time = pd.to_datetime(row["to_time"]).tz_localize(None)
        date = from_time.date()
        
        for label, slot_start, slot_end in fixed_slots:
            slot_start_dt = datetime.combine(date, slot_start)
            slot_end_dt = datetime.combine(date, slot_end)
            # If slot overlaps with stay duration, keep it
            if slot_end_dt > from_time and slot_start_dt < to_time:
                slots.append({
                    'participant': row['participant_id'],
                    'date': date,
                    'town': row['town'],
                    'time_slot': label
                })
    return slots

def generateHeatmap(input_df, input_y, input_x, input_color, input_color_theme):
    # Keep slot order consistent (top to bottom) based on fixed_slots
    slot_order = [s[0] for s in fixed_slots]

    # Computed field 'count_pos' to avoid log(0) + treat zeros as 1 just for coloring
    base = alt.Chart(input_df).transform_calculate(
        count_pos='max(datum.count, 1)'
    )
    
    # Determine domain for log scale
    max_count = input_df[input_color].max() # input_color = count column from df
    domain = [1, max_count]
    
    # Log color scale making mid/low values more perceptible
    color_enc = alt.Color(
        'count_pos:Q',
        scale=alt.Scale(
            type='log',
            scheme=input_color_theme,
            domain=domain
        ),
        legend=alt.Legend(title='People (log scale)')
    )
    # Heatmap creation
    heatmap = base.mark_rect().encode(
        x=alt.X(f'{input_x}:O',title='Towns',axis=alt.Axis(titleFontWeight='bold', titleFontSize=16)),
        y=alt.Y(f'{input_y}:O', sort=slot_order, title='Time slots', axis=alt.Axis(titleFontWeight='bold', titleFontSize=16)),
        color=color_enc,
        stroke=alt.value('black'),
        strokeWidth=alt.value(0.25),
        tooltip=[
            alt.Tooltip(f'{input_x}:N', title='Town'),
            alt.Tooltip(f'{input_y}:N', title='Time slot'),
            alt.Tooltip('count:Q', title='People number')
        ]
    )

    chart = (heatmap).properties(width=900).configure_axis(
        labelFontSize=12,
        titleFontSize=12
    )
    return chart


@st.cache_data
def compute_heatmap_data(input_df, input_day,) :
    
    # ====================================================================
    # Filter input_df to get only rows matching input_day
    # ====================================================================
        
    # Ensure input is a list
    if isinstance(input_day, str):
        input_day = [input_day]
        
    df_heatmap = input_df[
        input_df["day_start"].isin(input_day) 
    ].reset_index(drop=True)
    
    # ====================================================================
    
    df = df_heatmap.drop(columns=["start_geohash", "end_geohash","distance_km","start_date", 
                                "end_date", "journey_id"])
    
    # Ensure correct types
    df['start_time'] = pd.to_datetime(df['start_time']) 
    df['end_time'] = pd.to_datetime(df['end_time'])
    
    df['date_only'] = df['start_time'].dt.date # date_only is for example 2024-08-28
    
    # Sort entire dataframe for predictable iteration
    df = df.sort_values(by=['participant_id', 'date_only', 'start_time'])
    
    
    inferred_records = []


    # Group by participant and date
    grouped = df.groupby(['participant_id', 'date_only'])

    for (participant_id, date_only), group in grouped:
        group = group.sort_values(by='start_time').reset_index(drop=True)

        prev_end_time = None
        prev_end_town = None

        for idx, row in group.iterrows():
            start_time = row['start_time']
            end_time = row['end_time']
            start_town = row['StartingTown']
            end_town = row['EndingTown']

            # FIRST ROW of the day: from 00:00 to start_time => participant in starting_town
            if idx == 0:
                inferred_records.append({
                    'participant_id': participant_id,
                    'town': start_town,
                    'from_time': datetime.combine(start_time.date(), datetime.min.time()),
                    'to_time': start_time,
                    'date': date_only   
                })

            else:
                # Same day: 
                if prev_end_time.date() == start_time.date():
                    # check if current starting town == current end town
                    if start_town == end_town:
                        inferred_records.append({
                            'participant_id': participant_id,
                            'town': start_town,
                            'from_time': start_time,
                            'to_time': end_time,
                            'date': date_only
                        })
                    # check if prev end town == current start town
                    if prev_end_town == start_town:
                        inferred_records.append({
                            'participant_id': participant_id,
                            'town': start_town,
                            'from_time': prev_end_time,
                            'to_time': start_time,
                            'date': date_only
                        })
                    # check if prev end town != current start town
                    # [ in that case, there is probably a missing trip data 
                    #   I assume here that the participant stayed in previous end town 
                    #   during 1 hour. We can't inffer anything after ]
                    if prev_end_town != start_town:
                        an_hour_after = prev_end_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                        inferred_records.append({
                            'participant_id': participant_id,
                            'town': prev_end_town,
                            'from_time': prev_end_time,
                            'to_time': an_hour_after,
                            'date': date_only
                        })  
                        an_hour_before = start_time.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                        inferred_records.append({
                            'participant_id': participant_id,
                            'town': prev_end_town,
                            'from_time': an_hour_before,
                            'to_time': start_time,
                            'date': date_only
                        })
                        
                else:
                    # New day: finish yesterday in prev_end_town
                    inferred_records.append({
                        'participant_id': participant_id,
                        'town': prev_end_town,
                        'from_time': prev_end_time,
                        'to_time': datetime.combine(prev_end_time.date(), datetime.max.time()),
                        'date': date_only
                    })
                    # And today: from 00:00 to current start time in current start_town
                    inferred_records.append({
                        'participant_id': participant_id,
                        'town': start_town,
                        'from_time': datetime.combine(start_time.date(), datetime.min.time()),
                        'to_time': start_time,
                        'date': date_only
                    })

            # Update previous values
            prev_end_time = end_time
            prev_end_town = end_town

        # After last row of the day: fill until 23:59 in end_town
        inferred_records.append({
            'participant_id': participant_id,
            'town': prev_end_town,
            'from_time': prev_end_time,
            'to_time': datetime.combine(prev_end_time.date(), datetime.max.time()),
            'date': date_only
        })

    inferred_df = pd.DataFrame(inferred_records)  

    list_slots = getTimeSlot(inferred_df)
    df_slots = pd.DataFrame(list_slots, columns=['participant', 'date', 'town', 'time_slot'])
    df_slots_noDuplicates = df_slots.drop_duplicates(subset=['participant', 'date', 'town', 'time_slot'])

    # Then group and count
    df_heatmap_counts = df_slots_noDuplicates.groupby(['time_slot', 'town']).size().reset_index(name='count')
    
    # Get top 20 towns by total count across all time slots
    town_totals = df_heatmap_counts.groupby('town')['count'].sum().reset_index(name='total_count')
    top_20_towns = town_totals.sort_values('total_count', ascending=False).head(20)['town']
    
    # Filter df_heatmap_counts to include only top 20 towns
    df_heatmap_counts = df_heatmap_counts[df_heatmap_counts['town'].isin(top_20_towns)]
    
    # Ensure all time slots from fixed_slots are represented with count=0 if missing
    slot_order = [slot[0] for slot in fixed_slots]
    all_towns = top_20_towns.tolist()
    grid = pd.MultiIndex.from_product([slot_order, all_towns], names=['time_slot', 'town']).to_frame(index=False)
    df_full = grid.merge(df_heatmap_counts, on=['time_slot', 'town'], how='left')
    df_full['count'] = df_full['count'].fillna(0).astype(int)
    df_heatmap_counts = df_full
    
    return df_heatmap_counts
    
    
# MAIN method 
def heatmapArray(input_df, input_day):
    # Compute heatmap data
    df_heatmap_counts = compute_heatmap_data(input_df, input_day)
    # Check for empty data
    if df_heatmap_counts.empty:
        st.warning("⚠️ No data available for the selected filter.")
        return
    # Plot
    heatmap = generateHeatmap(df_heatmap_counts, 'time_slot', 'town', 'count', 'viridis')
    st.altair_chart(heatmap, use_container_width=True)
