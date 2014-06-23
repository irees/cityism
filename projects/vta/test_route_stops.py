import sys
import json

import cityism.planner
import cityism.geojson

if __name__ == "__main__":
  c = cityism.geojson.FeatureCollection()
  route = cityism.geojson.Feature()
  c.addfeature(route)

  stops = []
  with open(sys.argv[1]) as f:
    data = json.load(f)
    for feature in data['features']:
      geom = feature['geometry']
      if geom['type'] == 'Point':
        stops.append(geom['coordinates'])
        c.collection['features'].append(feature)

  # Flip coords
  stops = [(j,i) for i,j in stops]

  p = cityism.planner.getplanner('osrm')
  for i in range(len(stops)-1):
    start = stops[i]
    end = stops[i+1]
    a, _ = p.plan(start=start, end=end)

    route.addpoint(start[1], start[0])
    for i in a:
      route.addpoint(i[0], i[1])
    route.addpoint(end[1], end[0])
  
  print "Route:"
  with open(sys.argv[2], 'w') as f:
    f.write(c.dump())