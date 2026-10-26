import json
import os

with open('data/australian-states.min.json', 'r') as f:
    aus = json.load(f)

for feat in aus['features']:
    geom = feat['geometry']
    if geom['type'] == 'Polygon':
        geom['coordinates'] = [ring[::-1] for ring in geom['coordinates']]
    elif geom['type'] == 'MultiPolygon':
        geom['coordinates'] = [[ring[::-1] for ring in poly] for poly in geom['coordinates']]

with open('data/australian-states-fixed.json', 'w') as f:
    json.dump(aus, f)
print("Saved fixed topology to data/australian-states-fixed.json")