import json

class FeatureCollection(object):
  """A geojson FeatureCollection."""
  def __init__(self):
    self.collection = {
      "type": "FeatureCollection",
      "features": []
    }

  def addfeature(self, g):
    self.collection['features'].append(g.feature)
  
  def data(self):
    return self.collection

  def dump(self):
    return json.dumps(self.data())

class Feature(object):
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
  
  def setcoords(self, coords):
    self.feature['geometry']['coordinates'] = coords

  def getcoords(self):
    return self.feature['geometry']['coordinates']
  
  def addpoint(self, lon, lat):
    self.feature['geometry']['coordinates'].append((lon, lat))
    
  def data(self):
    return self.feature
