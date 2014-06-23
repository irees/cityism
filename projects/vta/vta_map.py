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
  # Find nearest roadway points and, ugh, flip again...
  # flip = [otp.nearest(i) for i in flip]
  # flip = map(lambda x:(x[1],x[0]), flip)

  # Find the longest paths...
  print "Looking for route between %s stops..."%len(flip)
  print flip

  for i in range(len(flip)-1):
    start = flip[i]
    end = flip[i+1]
    a, _ = otp.plan(start=start, end=end)
    route.extend(a)
  
  # i = 0
  # while i < len(flip):
  #   for j in range(len(flip), i, -1):
  #     chunk = flip[i:j]
  #     a, _ = otp.plan(start=chunk[0], end=chunk[-1], intermediate=chunk[1:-1])
  #     print "%s -> %s: found %s points"%(i, j, len(a))
  #     if a:
  #       i = j - 1
  #       route.extend(a)
  #       break
  #   i += 1        
  return route


  # for chunk in chunks(flip, 1):
  #   a, _ = otp.plan(start=chunk[0], end=chunk[-1], intermediate=chunk[1:-1])
  #   print "Stops: %s. Sent request with %s points, got %s points: extending:"%(len(stops), len(chunk), len(a))
  #   # if not a:
  #   #  a = chunk
  #   route.extend(a)
  # route.append(stops[-1])
  # return route

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
  
  def stops_as_geo(self):
    ret = []
    for count, stop in enumerate(self.stops):
      f = Feature(typegeom='Point', stop_sequence=count)
      f.setcoords((stop.stop.stop_lon, stop.stop.stop_lat))
      ret.append(f)
    return ret
  
  def route_as_geo(self, sched=None, planner=False, **kwargs):
    f = Feature(name=self.trip_headsign, **kwargs)
    # Check if we have shapes.txt...
    if self.trip.shape_id:
      # Ok, hacky patch to 'gtfs' to pull it out of the sqlite-sqlalchemy db.
      q = sched.session.query(gtfs.entity.ShapePoint).filter_by(shape_id=self.trip.shape_id)
      for stop in q.all():
        f.addpoint(stop.shape_pt_lon, stop.shape_pt_lat)
    else:
      # Otherwise, reconstruct the route based on stop locations.
      stops = [(stop.stop.stop_lon, stop.stop.stop_lat) for stop in self.stops]
      if planner:
        stops = route_from_stops(stops, planner=planner)
      for lon,lat in stops:
        f.addpoint(lon,lat)
    return f
    

##### Main #####

def headways(route, c=None, sched=None, planner=False):
  print "\n===== Route: %s ====="%(route)
  c = c or FeatureCollection()
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
  for headsign,trips in r.by_headsign().items()[:1]:
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
    f = trips[0].route_as_geo(sched=sched, planner=planner, **kwargs)
    c.addfeature(f)

    # Get the stops.
    for f in trips[0].stops_as_geo():
      c.addfeature(f)
      
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
  for route in routes:
    c = FeatureCollection()
    headways(route, c=c, sched=sched, planner=args.planner)
    with open("vta-%s.geojson"%route.route_id, 'w') as f:
      f.write(c.dump())
  
  # Write the geojson output.
  # if args.outfile:
  #   with open(outfile, "w") as f:
  #     print f.write(c.dump())
    
