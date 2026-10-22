import json

# 1. Load your existing file
with open("data/LGA_2025_AUST_GDA2020.json", "r") as f:
    data = json.load(f)

# 2. Wrap each raw geometry into a standard GeoJSON Feature
features = []
for geom in data.get("geometries", []):
    features.append({
        "type": "Feature",
        "properties": {}, # You can add LGA names here later if needed
        "geometry": geom
    })

# 3. Create the final FeatureCollection wrapper
feature_collection = {
    "type": "FeatureCollection",
    "features": features
}

# 4. Save the fixed map file
with open("data/vic_boundaries.geojson", "w") as f:
    json.dump(feature_collection, f)

print("Successfully created vic_boundaries.geojson!")