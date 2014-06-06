import urllib
import urllib2
import json

import polyline

def getplanner(planner='osrm'):
  planner = planner.lower()
  if planner == 'osrm':
    return OSRM()
  elif planner == 'otp':
    return OpenTripPlanner()

def fjoin(a):
  return ",".join(map(str, a))

class Planner(object):
  endpoint_default = None
  
  def __init__(self, endpoint=None):
    self.endpoint = endpoint or self.endpoint_default
  
  def call(self, method, **kwargs):
    print "CALL:", method, kwargs
    params = urllib.urlencode(kwargs, doseq=True)
    url = '%s/%s?%s'%(self.endpoint, method, params)
    print url
    response = urllib2.urlopen(url).read()
    response = json.loads(response)
    return response

  def plan(self, start, end, mode='CAR', intermediate=None):
    line = []
    duration = 0.0
    return line, duration

class OSRM(Planner):
  endpoint_default = "http://localhost:5000"  
  def plan(self, start, end, mode='CAR', intermediate=None):
    line = []
    duration = 0.0
    intermediate = intermediate or []
    loc = map(fjoin, [start] + intermediate + [end])
    response = self.call('viaroute', output='json', z=14, loc=loc)
    line = polyline.decode(response['route_geometry'])
    # Non standard polyline
    line = [(i/10.0, j/10.0) for i,j in line]
    return line, duration

class OpenTripPlanner(Planner):
  endpoint_default = "http://localhost:8080/otp-rest-servlet/ws"
  def plan(self, start, end, mode='CAR', intermediate=None):
    line = []
    duration = 0.0
    start = fjoin(start)
    end = fjoin(end)
    intermediate = map(fjoin, intermediate or [])
    try:
      response = self.call("plan", fromPlace=start, toPlace=end, mode=mode, intermediatePlaces=intermediate, intermediatePlacesOrdered='true')
      line = self._getline(response)
      duration = self._getduration(response)
    except Exception, e:
       print e
    return line, duration

  def _getduration(self, response):
    itin = response['plan']['itineraries'][0]
    return itin['duration']
  
  def _getline(self, response):  
    line = []
    itin = response['plan']['itineraries'][0]
    for leg in itin.get('legs', []):
      legline = leg['legGeometry']['points']
      legline = polyline.decode(legline)
      line.extend(legline)
    return line

if __name__ == "__main__":
  otp = OSRM()
  route, duration = otp.plan(start=(37.79398,-122.39524), end=(37.422,-122.084058), mode='CAR')
  import cityism.geojson
  c = cityism.geojson.GeoFeatureCollection()
  f = cityism.geojson.GeoFeature()
  for point in route:
    f.addpoint(point[0], point[1])
  c.addfeature(f)
  print c.dump()



