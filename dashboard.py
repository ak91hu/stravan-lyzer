import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="My Strava Dashboard",
    page_icon="👟",
    layout="wide"
)

# --- DATA LOADING AND CLEANING ---
@st.cache_data  # Cache the data to speed up app
def load_data():
    try:
        df = pd.read_csv("activities.csv")
    except FileNotFoundError:
        st.error("Error: 'activities.csv' file not found in the /app directory.")
        st.stop()

    # --- Date Conversions ---
    df['Activity Date'] = pd.to_datetime(df['Activity Date'])
    df.set_index('Activity Date', inplace=True)
    df.sort_index(inplace=True)

    # Extract time components for filtering and charts
    df['Year'] = df.index.year
    df['Month'] = df.index.month_name()
    df['Day of Week'] = df.index.day_name()
    df['Hour of Day'] = df.index.hour

    # --- Data Cleaning & Normalization ---

    # --- THIS IS THE FIX ---
    # Use 'Distance.1' (which is in meters) or fallback to 'Distance' (which is in km)
    if 'Distance.1' in df.columns:
        df['Distance_km'] = df['Distance.1'] / 1000  # Use the meters column
    elif 'Distance' in df.columns:
        df['Distance_km'] = df['Distance']  # Use the km column directly
    else:
        df['Distance_km'] = 0

    # Handle Moving Time (seconds to hours)
    if 'Moving Time' in df.columns:
        df['Moving_Time_hr'] = df['Moving Time'] / 3600
    else:
        df['Moving_Time_hr'] = 0

    # Handle Elevation Gain (checking for both common names)
    if 'Total Elevation Gain' in df.columns:
        df['Elevation_Gain_m'] = df['Total Elevation Gain']
    elif 'Elevation Gain' in df.columns:
        df['Elevation_Gain_m'] = df['Elevation Gain']
    else:
        df['Elevation_Gain_m'] = 0

    # Handle Average Speed (m/s to km/h)
    if 'Average Speed' in df.columns:
        df['Average_Speed_kmh'] = df['Average Speed'] * 3.6
    else:
        # Calculate from distance and time if possible
        if 'Distance_km' in df.columns and 'Moving_Time_hr' in df.columns:
             # Avoid division by zero
            df['Average_Speed_kmh'] = df.apply(
                lambda row: row['Distance_km'] / row['Moving_Time_hr'] if row['Moving_Time_hr'] > 0 else 0,
                axis=1
            )
        else:
            df['Average_Speed_kmh'] = 0

    # Handle Calories
    if 'Calories' not in df.columns:
        df['Calories'] = 0

    # Fill NaNs in key columns with 0 to prevent crashes
    key_cols = ['Distance_km', 'Moving_Time_hr', 'Elevation_Gain_m', 'Average_Speed_kmh', 'Calories']
    for col in key_cols:
        df[col] = df[col].fillna(0)

    # Replace infinite values (from division by zero) with 0
    df.replace([np.inf, -np.inf], 0, inplace=True)

    return df

df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Your Data")

# Year Filter
all_years = ["All Years"] + sorted(df['Year'].unique(), reverse=True)
selected_year = st.sidebar.selectbox(
    "Select Year:",
    options=all_years,
    index=0 # Default to "All Years"
)

# Filter data by Year
if selected_year == "All Years":
    df_filtered = df.copy()
else:
    df_filtered = df[df['Year'] == selected_year]

# Activity Type Filter
all_types = ["All Activities"] + sorted(df_filtered['Activity Type'].unique().tolist())
selected_types = st.sidebar.multiselect(
    "Select Activity Type(s):",
    options=all_types,
    default="All Activities"
)

# Filter data by Activity Type
if "All Activities" in selected_types or not selected_types:
    # No change, df_filtered is already set by year
    pass
else:
    df_filtered = df_filtered[df_filtered['Activity Type'].isin(selected_types)]

# Check if filter selections resulted in empty data
if df_filtered.empty:
    st.warning("No activities found for the selected filters.")
    st.stop()

# --- MAIN PAGE & DASHBOARD ---
st.title("My Strava Dashboard")
st.markdown(f"Displaying data for: **{selected_year}** | Activity Types: **{', '.join(selected_types)}**")

# --- TOP-LEVEL METRICS (KPIs) ---
total_activities = df_filtered.shape[0]
total_distance = df_filtered['Distance_km'].sum()
total_time = df_filtered['Moving_Time_hr'].sum()
total_elevation = df_filtered['Elevation_Gain_m'].sum()
total_calories = df_filtered['Calories'].sum()

# Calculate averages, handling division by zero
avg_distance = total_distance / total_activities if total_activities > 0 else 0
avg_time = total_time / total_activities if total_activities > 0 else 0
# For average speed, mean of means is more representative than total_dist / total_time
avg_speed = df_filtered[df_filtered['Average_Speed_kmh'] > 0]['Average_Speed_kmh'].mean()


col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Activities", f"{total_activities:,}")
col2.metric("Total Distance", f"{total_distance:,.1f} km")
col3.metric("Total Time", f"{total_time:,.1f} hrs")
col4.metric("Total Elevation", f"{total_elevation:,.0f} m")

col1a, col2a, col3a, col4a = st.columns(4)
col1a.metric("Total Calories", f"{total_calories:,.0f}")
col2a.metric("Avg. Distance", f"{avg_distance:,.1f} km")
col3a.metric("Avg. Time", f"{avg_time:,.1f} hrs")
col4a.metric("Avg. Speed", f"{avg_speed:,.1f} km/h")

st.markdown("---")

# --- CHART TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["Monthly Stats", "Heatmaps", "Breakdown", "Recent Activities"])

with tab1:
    # Chart 1: Distance per Month (Stacked Bar)
    st.header("Distance per Month by Activity Type")
    df_monthly_typed = df_filtered.groupby('Activity Type').resample('M')['Distance_km'].sum().reset_index()
    df_monthly_typed['Activity Date'] = df_monthly_typed['Activity Date'].dt.strftime('%Y-%m') # Format for better axis

    fig_monthly = px.bar(
        df_monthly_typed,
        x='Activity Date',
        y='Distance_km',
        color='Activity Type',
        labels={'Distance_km': 'Total Distance (km)', 'Activity Date': 'Month'}
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

    # Chart 2: Cumulative Distance
    st.header("Cumulative Distance Over Time")
    df_cumulative = df_filtered.sort_index()
    df_cumulative['Cumulative Distance'] = df_cumulative['Distance_km'].cumsum()
    fig_cumulative = px.line(
        df_cumulative.reset_index(),
        x='Activity Date',
        y='Cumulative Distance',
        title="My Cumulative Distance",
        color='Activity Type',
        labels={'Cumulative Distance': 'Total Distance (km)', 'Activity Date': 'Date'}
    )
    st.plotly_chart(fig_cumulative, use_container_width=True)

with tab2:
    st.header("Activity Heatmaps")
    # Define order for charts
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    # --- NEW: HOURLY HEATMAP ---
    st.subheader("Activity by Hour and Day of Week")
    hour_day_data = df_filtered.pivot_table(
        index='Hour of Day',
        columns='Day of Week',
        values='Distance_km',
        aggfunc='sum'
    ).reindex(columns=day_order)

    fig_hour_day = px.imshow(
        hour_day_data,
        labels=dict(x="Day of Week", y="Hour of Day", color="Distance (km)"),
        title="Heatmap of Total Distance by Hour and Day",
        aspect="auto"
    )
    st.plotly_chart(fig_hour_day, use_container_width=True)

    # Split remaining heatmaps into columns
    col_h1, col_h2, col_h3 = st.columns(3)

    with col_h1:
        # Heatmap 1: Total Distance
        st.subheader("Total Distance")
        heatmap_dist = df_filtered.pivot_table(
            index='Day of Week',
            columns='Month',
            values='Distance_km',
            aggfunc='sum'
        ).reindex(index=day_order, columns=month_order)

        fig_heatmap_dist = px.imshow(
            heatmap_dist,
            labels=dict(color="Distance (km)"),
            aspect="auto"
        )
        st.plotly_chart(fig_heatmap_dist, use_container_width=True)

    with col_h2:
        # --- NEW: AVG SPEED HEATMAP ---
        st.subheader("Average Speed")
        heatmap_speed = df_filtered.pivot_table(
            index='Day of Week',
            columns='Month',
            values='Average_Speed_kmh',
            aggfunc='mean' # Use mean for average speed
        ).reindex(index=day_order, columns=month_order)

        fig_heatmap_speed = px.imshow(
            heatmap_speed,
            labels=dict(color="Avg. Speed (km/h)"),
            color_continuous_scale=px.colors.sequential.YlOrRd, # Different color scale
            aspect="auto"
        )
        st.plotly_chart(fig_heatmap_speed, use_container_width=True)

    with col_h3:
        # --- NEW: ACTIVITY COUNT HEATMAP ---
        st.subheader("Activity Count")
        # Use a non-numeric column like 'Activity Name' for counting
        heatmap_count = df_filtered.pivot_table(
            index='Day of Week',
            columns='Month',
            values='Activity Name', # Any non-numeric column works
            aggfunc='count' # Count occurrences
        ).reindex(index=day_order, columns=month_order)

        fig_heatmap_count = px.imshow(
            heatmap_count,
            labels=dict(color="Count"),
            color_continuous_scale=px.colors.sequential.Greens, # Different color scale
            aspect="auto"
        )
        st.plotly_chart(fig_heatmap_count, use_container_width=True)

with tab3:
    # Table 1: Detailed Breakdown by Activity Type
    st.header("Breakdown by Activity Type")
    df_summary = df_filtered.groupby('Activity Type').agg(
        Total_Activities=('Distance_km', 'size'),
        Total_Distance_km=('Distance_km', 'sum'),
        Total_Time_hr=('Moving_Time_hr', 'sum'),
        Total_Elevation_m=('Elevation_Gain_m', 'sum'),
        Avg_Speed_kmh=('Average_Speed_kmh', lambda x: x[x > 0].mean()) # More robust avg
    ).reset_index().sort_values(by='Total_Distance_km', ascending=False)

    # Format for display
    df_summary['Total_Distance_km'] = df_summary['Total_Distance_km'].round(1)
    df_summary['Total_Time_hr'] = df_summary['Total_Time_hr'].round(1)
    df_summary['Total_Elevation_m'] = df_summary['Total_Elevation_m'].round(0)
    df_summary['Avg_Speed_kmh'] = df_summary['Avg_Speed_kmh'].fillna(0).round(1)

    st.dataframe(df_summary, use_container_width=True, hide_index=True)

with tab4:
    # Table 2: Recent Activities
    st.header("Recent Activities")
    recent_cols = ['Activity Name', 'Activity Type', 'Distance_km', 'Moving_Time_hr', 'Average_Speed_kmh', 'Elevation_Gain_m']
    # Ensure all columns exist before trying to display them
    display_cols = [col for col in recent_cols if col in df_filtered.columns]

    st.dataframe(
        df_filtered[display_cols].sort_index(ascending=False).head(20).round(1),
        use_container_width=True
    )

# --- Show Raw Data (Optional) ---
if st.checkbox("Show raw filtered data table"):
    st.subheader("Raw Data")
    st.write(df_filtered)
