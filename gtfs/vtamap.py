"""Valley Transportation Authority analysis."""
import sys
import os
import collections
import math
import datetime
import dateutil
import numpy
import json

# import transitfeed
import gtfs

class Collection(object):
  def __init__(self):
    self.collection = {
      "type": "FeatureCollection",
      "features": []
    }

  def add(self, feature):
    self.collection['features'].append(feature.feature)
  
  def data(self):
    return self.collection

  def dump(self):
    return json.dumps(self.data())

class Feature(object):
  def __init__(self, typegeom="LineString", coords=None, **kwargs):
    self.feature = {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": typegeom,
        "coordinates": coords or []
      }
    }
    
  def addpoint(self, lon, lat):
    self.feature['geometry']['coordinates'].append((lon, lat))
    
  def data(self):
    return self.feature

def routes(sched):
  for route in sched.routes:
    f = Feature()
    if not route.trips:
      continue

    print "===== Route: %s ====="%(route)
    starts = []
    durations = []

    # Resort
    print "Sorting..."
    trips = []
    for trip in route.trips:
      stops = sorted(trip.stop_times, key=lambda x:x.stop_sequence)
      start = stops[0].arrival_time.val
      end = stops[-1].arrival_time.val
      duration = end - start
      trips.append((start, duration))
      
    trips = sorted(trips)
    for i in trips:
      print i
    headways = [i[0] for i in trips]
    headways = sorted(set(headways)) # ugh..
    headways = [headways[i+1] - headways[i] for i in range(len(headways)-1)]
    durations = [i[1] for i in trips]

    print "Headways:", headways
    for i in range(0, 110, 10):
      print "\t", i, "\t", numpy.percentile(headways, i)

    print "Durations:", durations
    for i in range(0, 110, 10):
      print "\t", i, "\t", numpy.percentile(durations, i)


if __name__ == "__main__":
  filename = sys.argv[1]
  sched = gtfs.Schedule(filename)
  routes(sched)