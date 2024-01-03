import gpxpy
import streamlit as st
import pandas as pd
import geopandas as gpd
import os

base_gpx_path = "garmin-connect-export/2024-01-02_garmin_connect_export"
gpx_paths = [
    os.path.join(base_gpx_path, p)
    for p in os.listdir(base_gpx_path)
    if p.endswith(".gpx")
]

activities_csv_path = base_gpx_path + "/activities.csv"

def gpx_to_geopandas(gpx_file_path):
    gpx_file = open(gpx_file_path, "r")
    gpx = gpxpy.parse(gpx_file)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append([point.latitude, point.longitude])

    df = pd.DataFrame(data, columns=["Latitude", "Longitude"])
    df.rename(columns={"Latitude": "latitude", "Longitude": "longitude"}, inplace=True)
    # Convert DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude))

    return gdf


def main():
    st.set_page_config(page_title="Renato", page_icon="🔥")

    st.title("Hello, Streamlit!")
    st.write("This is a basic Streamlit application.")

    selected_option = st.selectbox("Select an option:", gpx_paths)

    st.write(f"You selected: {selected_option}")

    # Read data from a GPX file
    data = gpx_to_geopandas(selected_option)
    # Display a map with the latitude and longitude values
    st.map(data, size=2, color="#0044ff")
    activities_df = pd.read_csv(activities_csv_path)
    st.write(activities_df)

if __name__ == "__main__":
    main()
