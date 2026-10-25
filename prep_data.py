"""
prep_data.py - Builds Australia-wide data/sightings.csv (all 8 states, 9 species)
and data/state_sightings.csv, and fixes GeoJSON winding order.
"""
import glob
import os
import json
import numpy as np
import pandas as pd

def fix_winding_order(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r") as f:
        data = json.load(f)
    geoms = data["geometries"] if "geometries" in data else [feat["geometry"] for feat in data["features"]]
    for g in geoms:
        if g["type"] == "Polygon":
            g["coordinates"] = [ring[::-1] for ring in g["coordinates"]]
        elif g["type"] == "MultiPolygon":
            g["coordinates"] = [[ring[::-1] for ring in poly] for poly in g["coordinates"]]
    fixed_path = filepath.replace(".min.json", "-fixed.json").replace(".json", "-fixed.json")
    with open(fixed_path, "w") as f:
        json.dump(data, f)
    print(f"Saved fixed map: {fixed_path}")

fix_winding_order("data/australian-states.min.json")
fix_winding_order("data/LGA_2025_AUST_GDA2020.json")

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

STATE_ABBR = {
    "New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD",
    "South Australia": "SA", "Western Australia": "WA", "Tasmania": "TAS",
    "Northern Territory": "NT", "Australian Capital Territory": "ACT",
}

CAPITALS = {
    "NSW": (-33.8688, 151.2093), "VIC": (-37.8136, 144.9631), "QLD": (-27.4705, 153.0260),
    "SA":  (-34.9285, 138.6007), "WA":  (-31.9505, 115.8605), "TAS": (-42.8821, 147.3272),
    "NT":  (-12.4634, 130.8456), "ACT": (-35.2809, 149.1300),
}

frames = []
for path in sorted(glob.glob("data/*.csv")):
    raw_name = os.path.basename(path).replace("_data.csv", "").replace(".csv", "")
    key = raw_name.replace("-", "_")
    if key not in SPECIES:
        continue
    name, group = SPECIES[key]
    d = pd.read_csv(path)

    t = pd.to_datetime(d["eventDate"], utc=True, errors="coerce")
    d["hour"] = t.dt.hour.fillna(0).astype(int)
    d["has_time"] = ~((t.dt.hour == 0) & (t.dt.minute == 0))
    d["species"], d["group"] = name, group

    if "stateProvince" in d.columns:
        d["stateProvince"] = d["stateProvince"].astype(str).str.strip()
    else:
        d["stateProvince"] = "Victoria"

    d = d[d["stateProvince"].isin(STATE_ABBR.keys())].copy()
    d["state_abbr"] = d["stateProvince"].map(STATE_ABBR)
    d["lat"] = d["decimalLatitude"].round(3)
    d["lon"] = d["decimalLongitude"].round(3)

    cap_lats = d["state_abbr"].map(lambda x: CAPITALS[x][0])
    cap_lons = d["state_abbr"].map(lambda x: CAPITALS[x][1])
    la1, lo1 = np.radians(d["lat"]), np.radians(d["lon"])
    la2, lo2 = np.radians(cap_lats), np.radians(cap_lons)
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    d["km_cbd"] = (12742 * np.arcsin(np.sqrt(a))).round(1)

    cols = ["species", "group", "stateProvince", "state_abbr", "year", "month", "hour", "has_time", "lat", "lon", "km_cbd"]
    frames.append(d[cols])
    print(f"{name:26s}: {len(d):7,d} Australia-wide rows")

out_all = pd.concat(frames, ignore_index=True)

# Save ALL Australia sightings to data/sightings.csv
out_all.to_csv("data/sightings.csv", index=False)
print(f"Saved data/sightings.csv: {len(out_all):,d} rows")

# Save pre-aggregated state_sightings.csv
state_summary = (
    out_all.groupby(["stateProvince", "state_abbr", "species", "group", "year", "month"])
    .size()
    .reset_index(name="sightings")
)
state_summary.to_csv("data/state_sightings.csv", index=False)
print(f"Saved data/state_sightings.csv: {len(state_summary):,d} rows")