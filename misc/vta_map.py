"""Valley Transportation Authority analysis."""
import sys
import os
import collections
import math
import datetime
import dateutil
import numpy
import json
import argparse

import gtfs

##### Routes #####

class Route(object):
  """Transit route."""
  def __init__(self, route=None, route_id=None, trips=None):
    self.route = route
    self.route_id = route_id
    self.trips = trips or []
  
  def add_trip(self, trip):
    self.trips.append(trip)
    
  def by_headsign(self):
    h = collections.defaultdict(list)
    for trip in self.trips:
      h[trip.trip_headsign].append(trip)
    return h

class Trip(object):
  """A Trip on a transit Route."""
  def __init__(self, trip_headsign=None, stops=None, trip=None):
    self.trip = trip
    self.trip_headsign = trip_headsign
    self.stops = stops or []

  def start_time(self):
    return self.stops[0].arrival_time.val
  
  def end_time(self):  
    return self.stops[-1].arrival_time.val
  
  def duration(self):
    return self.end_time() - self.start_time()
  
  def as_geo(self, sched=None, **kwargs):
    f = GeoFeature(name=self.trip_headsign, **kwargs)
    # Check if we have shapes.txt...
    if self.trip.shape_id:
      # Ok, hacky patch to 'gtfs' to pull it out of the sqlite-sqlalchemy db.
      q = sched.session.query(gtfs.entity.ShapePoint).filter_by(shape_id=self.trip.shape_id)
      for stop in q.all():
        f.addpoint(stop.shape_pt_lon, stop.shape_pt_lat)
    else:
      # Otherwise, reconstruct the route based on stop locations.
      for stop in self.stops:
        f.addpoint(stop.stop.stop_lon, stop.stop.stop_lat)
    return f
    
##### GeoJSON #####

class GeoFeatureCollection(object):
  """A geojson FeatureCollection."""
  def __init__(self):
    self.collection = {
      "type": "FeatureCollection",
      "features": []
    }

  def add_feature(self, g):
    self.collection['features'].append(g.feature)
  
  def data(self):
    return self.collection

  def dump(self):
    return json.dumps(self.data())

class GeoFeature(object):
  """A geojson Feature."""
  def __init__(self, typegeom="LineString", coords=None, **kwargs):
    self.feature = {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": typegeom,
        "coordinates": coords or []
      }
    }
    self.feature['properties'].update(kwargs)
    
  def addpoint(self, lon, lat):
    self.feature['geometry']['coordinates'].append((lon, lat))
    
  def data(self):
    return self.feature

##### Main #####

def headways(route, c=None, sched=None):
  print "\n===== Route: %s ====="%(route)
  c = c or GeoFeatureCollection()
  r = Route(route_id=route.route_id, route=route)

  # Group by headsign
  for trip in route.trips:
    # Weekend service -- skip
    if str(trip.service_period.monday) == '0':
      continue
     # Sort the stops by stop_sequence
    stops = sorted(trip.stop_times, key=lambda x:x.stop_sequence)
    t = Trip(trip_headsign=trip.trip_headsign, stops=stops, trip=trip)
    r.add_trip(t)

  # Calculate frequencies and build the route shape.
  for headsign,trips in r.by_headsign().items():
    trips = sorted(trips, key=lambda x:x.start_time())
    times = [trip.start_time() for trip in trips]
    endofday = (24*60*60) - times[-1] + times[0]
    durations = [trip.duration() for trip in trips]
    headways = [times[i+1] - times[i] for i in range(len(times)-1)]
    headways.append(endofday)
    
    print "\nHeadsign: %s"%headsign
    for i,j,k in zip(times, durations, headways):
      print "\tStart: %s, duration: %s, next bus in: %s"%(i,j,k)
    
    print "Vehicles per hour:"
    bins = [0]*24
    for i in times:
      # Midnight case.
      if i >= (24*60*60):
        i = 0
      bins[i/(60*60)] += 1
    for i,j in enumerate(bins):
      print "\t%s\t%s"%(i,j)

    print "Headways:"
    for i in [0, 25, 50, 75, 100]:
      print "\t%s:\t%s"%(i,numpy.percentile(headways, i))

    kwargs = {
      'headways': headways,
      'headway_min': min(headways),
      'headway_25': numpy.percentile(headways, 25),
      'headway_median': numpy.percentile(headways, 50),
      'headway_75': numpy.percentile(headways, 75),
      'headway_max': max(headways),
      'headway_peak': min([i for i in headways if i > 300]),
      'trips': times,
      'trip_count': len(trips),
      'route_id': route.route_id
    }

    # Get the shape. This is hacky.
    f = trips[0].as_geo(sched=sched, **kwargs)
    c.add_feature(f)
    
if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", help="GTFS .zip file, or cached sqlite DB.")
  parser.add_argument("outfile", help="GeoJSON output file.")
  parser.add_argument("--route", help="Run for route; helpful for debugging.", action="append")
  parser.add_argument("--exclude", help="Exclude routes", action="append")
  args = parser.parse_args()
  filename = args.filename
  outfile = args.outfile
  
  # Open the GTFS .zip or cache-y sqlite version.
  if filename.endswith(".db"):
    sched = gtfs.Schedule(filename)
  elif filename.endswith(".zip"):
    sched = gtfs.load(filename)

  # Get routes
  routes = sched.routes
  if args.route:
    routes = [i for i in sched.routes if i.route_id in args.route]
  if args.exclude:
    routes = [i for i in sched.routes if i.route_id not in args.exclude]

  # Create the collection, then go through the routes
  #   and calculate the headways and route shapes.
  c = GeoFeatureCollection()
  for route in routes:
    headways(route, c=c, sched=sched)
  
  # Write the geojson output.
  with open(outfile, "w") as f:
    print f.write(c.dump())
    
