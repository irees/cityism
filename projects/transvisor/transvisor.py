"""Transit Visualization. Forked from vta_map.py"""
import collections
import numpy
import json
import argparse
import pprint

import pygtfs as pygtfs

import cityism.planner
from cityism.geojson import *

def chunks(l, n):
  for i in range(1, len(l), n): 
    yield l[i-1:i+n]
  
def route_from_stops(stops, planner):
  # Flip from lon/lat -> lat/lon
  route = []
  otp = cityism.planner.getplanner(planner)
  flip = map(lambda x:(x[1],x[0]), stops)
  for i in range(len(flip)-1):
    start = flip[i]
    end = flip[i+1]
    a, _ = otp.plan(start=start, end=end)
    route.extend(a)  
  return route

##### Routes #####

class Route(object):
  """Transit route."""
  def __init__(self, route=None, trips=None):
    self.route = route
    self.trips = trips or []
  
  def add_trip(self, trip):
    self.trips.append(trip)
    
  def by_headsign(self):
    h = collections.defaultdict(list)
    for trip in self.trips:
      # print pprint.pprint(vars(trip.trip))
      t = '%s (%s)'%(trip.trip.trip_headsign, trip.trip.direction_id)
      h[t].append(trip)
    return h
  
class Trip(object):
  """A Trip on a transit Route."""
  def __init__(self, stops=None, trip=None):
    self.trip = trip
    self.stops = stops or []

  def start_time(self):
    return self.stops[0].arrival_time.seconds
  
  def end_time(self):  
    return self.stops[-1].arrival_time.seconds
  
  def duration(self):
    return self.end_time() - self.start_time()
  
  def as_geo(self, sched=None, planner=False, **kwargs):
    f = Feature(**kwargs)

    # Get the stops
    f.setproperty('stops', [stop.stop_id for stop in self.stops])

    # Check if we have shapes.txt...
    if self.trip.shape_id:
      # Ok, hacky patch to pygtfs to pull it out of the sqlite-sqlalchemy db.
      q = sched.session.query(pygtfs.gtfs_entities.ShapePoint).filter_by(shape_id=self.trip.shape_id)
      for stop in q.all():
        f.addpoint(stop.shape_pt_lon, stop.shape_pt_lat)
    else:
      # Otherwise, reconstruct the route based on stop locations.
      stops = [(stop.stop.stop_lon, stop.stop.stop_lat) for stop in self.stops]
      if planner:
        # Try to use a trip planner
        stops = route_from_stops(stops, planner=planner)
      for lon,lat in stops:
        # Otherwise, just a simple line
        f.addpoint(lon,lat)
    return f
    
class Stop(object):
  def __init__(self, stop=None, stop_id=None):
    self.stop = stop
    self.stop_id = stop_id
    
  def as_geo(self):
    f = Feature(name=str(self.stop), typegeom='Point')
    f.setcoords((self.stop.stop_lon, self.stop.stop_lat))
    return f
    
##### Main #####

def stopinfo(stop, sched=None):
  s = Stop(stop_id=stop.stop_id, stop=stop)
  f = s.as_geo()
  yield f
  
def routeinfo(route, sched=None, planner=False):
  print "\n===== Route: %s ====="%(route)
  r = Route(route=route)

  # Group by headsign
  for trip in route.trips:
    # Weekend service -- skip
    if not trip.service.monday:
      continue
    # Sort the stops by stop_sequence
    stops = sorted(trip.stop_times, key=lambda x:x.stop_sequence)
    t = Trip(stops=stops, trip=trip)
    r.add_trip(t)

  # Calculate frequencies and build the route shape.
  for headsign,trips in r.by_headsign().items():
    trips = sorted(trips, key=lambda x:x.start_time())
    times = [trip.start_time() for trip in trips]
    kwargs = {
      'trips': times,
      'route_id': route.route_id,
      'name': headsign
    }
    # Get the shape. This is hacky.
    f = trips[0].as_geo(sched=sched, planner=planner, **kwargs)
    yield f
    
if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", help="GTFS .zip file, or cached sqlite DB.")
  parser.add_argument("--outfile", help="GeoJSON output file.")
  parser.add_argument("--route", help="Run for route; helpful for debugging.", action="append")
  parser.add_argument("--exclude", help="Exclude routes", action="append")
  parser.add_argument("--planner", help="Reconstruct routes using a trip planner: osrm or otp")
  args = parser.parse_args()
  filename = args.filename
  outfile = args.outfile
  
  # Open the GTFS .zip or cache-y sqlite version.
  if filename.endswith(".db"):
    sched = pygtfs.Schedule(filename)
  elif filename.endswith(".zip"):
    sched = pygtfs.Schedule(":memory:")
    pygtfs.append_feed(sched, filename)

  # Get routes
  routes = sched.routes
  print "Routes:", routes
  if args.route:
    routes = [i for i in sched.routes if i.route_id in args.route]
  if args.exclude:
    routes = [i for i in sched.routes if i.route_id not in args.exclude]

  # Create the collection
  c = FeatureCollection()
  
  # Calculate route stats and add to collection
  for route in routes:
    for f in routeinfo(route, sched=sched, planner=args.planner):
      c.addfeature(f)

  # Get the stops
  # for stop in sched.stops:
  #   for f in stopinfo(stop, sched=sched):
  #     c.addfeature(f)
  
  # Write the geojson output.
  if args.outfile:
    with open(outfile, "w") as f:
      print f.write(c.dump())
    
