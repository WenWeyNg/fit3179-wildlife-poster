"""
prep_data.py  -  combine the nine species files into ONE small CSV for Vega-Lite.
Run from the project root:  python prep_data.py
Needs: pip install pandas numpy geopandas
"""
import glob, os
import numpy as np
import pandas as pd
import geopandas as gpd

# file name (without _data.csv / .csv)  ->  (nice name, group)
SPECIES = {
    "australian_magpie":        ("Australian Magpie",        "Native bird"),
    "australian_king_parrot":   ("Australian King-Parrot",   "Native bird"),
    "rainbow_lorikeet":         ("Rainbow Lorikeet",         "Native bird"),
    "noisy_miner":              ("Noisy Miner",              "Native bird"),
    "indian_myna":              ("Indian Myna",              "Invasive bird"),
    "common_blackbird":         ("Common Blackbird",         "Invasive bird"),
    "common_brushtail_possum":  ("Common Brushtail Possum",  "Mammal"),
    "grey_headed_flying_fox":   ("Grey-headed Flying-fox",   "Mammal"),
    "garden_sunskink":          ("Garden Sunskink",          "Reptile"),
}
CBD = (-37.8136, 144.9631)   # Melbourne GPO / CBD

def km_from_cbd(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    la0, lo0 = np.radians(CBD[0]), np.radians(CBD[1])
    a = np.sin((la - la0) / 2) ** 2 + np.cos(la) * np.cos(la0) * np.sin((lo - lo0) / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))

frames = []
for path in glob.glob("data/*.csv"):
    key = os.path.basename(path).replace("_data.csv", "").replace(".csv", "")
    if key not in SPECIES:
        continue
    name, group = SPECIES[key]
    d = pd.read_csv(path)
    
    # IMPORTANT: the 'Z' on eventDate is misleading - the clock time is already LOCAL time
    # (skinks peak ~12 noon, possums ~9pm). So do NOT convert time zones.
    t = pd.to_datetime(d["eventDate"], utc=True)
    d["hour"] = t.dt.hour
    d["has_time"] = ~((t.dt.hour == 0) & (t.dt.minute == 0))   # 00:00 = date only, no real time
    d["species"], d["group"] = name, group
    d["lat"] = d["decimalLatitude"].round(3)       # ~100 m, hides exact backyards, shrinks file
    d["lon"] = d["decimalLongitude"].round(3)
    d["km_cbd"] = km_from_cbd(d["lat"], d["lon"]).round(1)
    frames.append(d[["species", "group", "year", "month", "hour", "has_time", "lat", "lon", "km_cbd"]])
    print(f"{name:26s}{len(d):6d} rows")

out = pd.concat(frames, ignore_index=True)

# ---- STEP 2: Join to LGA boundaries using GeoPandas -------------------------
print("\nLoading ABS Shapefile to calculate LGA boundaries...")

# Load the downloaded ABS LGA shapefile
# Ensure LGA_2025_AUST_GDA2020.shp is in the same directory you run the script from
lga = gpd.read_file("LGA_2025_AUST_GDA2020.shp")

# Filter strictly for Victoria (State Code '2' in the ABS structure)
# The column name might vary slightly depending on the ABS export year, usually 'STE_NAME21' or 'STE_NAME25'
state_col = [col for col in lga.columns if 'STE_NAME' in col][0]
vic_lga = lga[lga[state_col] == 'Victoria'].copy()

# Convert our wildlife CSV data into a spatial GeoDataFrame using lat/lon
pts = gpd.GeoDataFrame(
    out, 
    geometry=gpd.points_from_xy(out.lon, out.lat), 
    crs="EPSG:4326" # Standard GPS coordinates
)

# Transform the points to match the shapefile's Coordinate Reference System (GDA2020)
pts = pts.to_crs(vic_lga.crs)

# Perform the Spatial Join: which polygon does each point fall inside?
lga_code_col = [col for col in vic_lga.columns if 'LGA_CODE' in col][0]
joined = gpd.sjoin(pts, vic_lga[[lga_code_col, "geometry"]], predicate="within", how="left")

# Assign the resulting ABS LGA Code back to our main dataset
out["lga_code"] = joined[lga_code_col]

# Save the final consolidated file
out.to_csv("sightings.csv", index=False)
print("\nsightings.csv saved:", len(out), "rows,", round(os.path.getsize("sightings.csv") / 1e6, 2), "MB")