import urllib
import urllib2
import json

import polyline

DEFAULT_ENDPOINT = "http://localhost:8080/otp-rest-servlet/ws"

class OpenTripPlanner(object):
  def __init__(self, endpoint=DEFAULT_ENDPOINT):
    self.endpoint = endpoint
  
  def call(self, method, **kwargs):
    print "CALL:", method, kwargs
    params = urllib.urlencode(kwargs)
    url = '%s/%s?%s'%(self.endpoint, method, params)
    response = urllib2.urlopen(url).read()
    response = json.loads(response)
    return response
  
  def getduration(self, response):
    itin = response['plan']['itineraries'][0]
    return itin['duration']
  
  def getline(self, response):  
    line = []
    itin = response['plan']['itineraries'][0]
    for leg in itin.get('legs', []):
      legline = leg['legGeometry']['points']
      legline = cityism.polyline.decode(legline)
      line.extend(legline)
    return line
    
  def plan(self, start, end, mode='CAR'):
    line = None
    duration = 0.0
    try:
      response = self.call("plan", fromPlace=start, toPlace=end, mode=mode)
      line = self.getline(response)
      duration = self.getduration(response)
    except Exception, e:
      print e
    return line, duration

if __name__ == "__main__":
  otp = OpenTripPlanner()
  print otp.plan(start=(37.79398,-122.39524), end=(37.422,-122.084058), mode='CAR')
  
  
  