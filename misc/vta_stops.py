import csv
import json
import sys

# FID,StopNo,RTIstop,BSID,STPNAM,Lat,Long,wkdyons,wkdyoffs,satons,satoffs,sunons,sunoffs,allons,alloffs,Combined,Rank
stops = []
with open(sys.argv[1], 'rU') as f:
  reader = csv.reader(f)
  header = reader.next()
  header = map(str.lower, header)
  for row in reader:
    data = {}
    for k,v in zip(header, row):
      try:
        v = float(v)
      except:
        pass
      data[k] = v
    stops.append(data)

c = {
  "type": "FeatureCollection",
  "features": []
}

stops = sorted(stops, key=lambda x:x.get('combined'))[:50]

for stop in stops:
  lat = float(stop.pop('lat', 0.0))
  lon = float(stop.pop('long', 0.0))
  f = {
        "type": "Feature",
        "properties": data,
        "geometry": {
          "type": "Point",
          "coordinates": [lon, lat]
        }
    }
  c['features'].append(f)

print json.dumps(c)
    