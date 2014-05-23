"""Animation of housing units built by decade."""
import os
import argparse
import numpy
import matplotlib.pyplot as plt
import psycopg2.extras
import cityism.config
from cityism.utils import *

import pyproj

import mapnik

COASTLINE = '/Volumes/irees/data/maps/osm/land-polygons-complete-4326/land_polygons.shp'
MOTORWAYS = '/Volumes/irees/data/maps/osm/motorways_osm/motorways_osm.shp'

def cmaprgb(cmap, value):
  return '#%02X%02X%02X'%(cmap(value, bytes=True)[:3])

def projmerc(lon, lat):
  # Transform
  p1 = pyproj.Proj(init='epsg:4326')
  p2 = pyproj.Proj(init='epsg:3857')
  x, y = pyproj.transform(p1,p2,lon,lat)
  return x, y

class HousingAnimation(object):
  def __init__(self, m=None):
    # Setup the base map
    self.m = m or self.setup_map()
    self.setup_styles()

  def setup_map(self, m=None):
    m = mapnik.Map(1024, 1024)
    m.background = mapnik.Color('#b8dee6')
    return m

  def setup_styles(self):
    # Setup the styles
    # ... coastline
    style = mapnik.Style()
    rule = mapnik.Rule()
    rule.symbols.append(mapnik.PolygonSymbolizer(mapnik.Color('#ffffff')))
    style.rules.append(rule)
    self.m.append_style('coastline', style)

    # ... motorways
    style = mapnik.Style()
    rule = mapnik.Rule()
    rule.symbols.append(mapnik.LineSymbolizer(mapnik.Color('#666666'), 0.5))
    style.rules.append(rule)
    self.m.append_style('motorways', style)

    # ... key labels
    style = mapnik.Style()
    rule = mapnik.Rule()
    p = mapnik.TextSymbolizer(mapnik.Expression('[name]'), 'DejaVu Sans Book', 30, mapnik.Color('black'))
    rule.symbols.append(p)
    style.rules.append(rule)
    self.m.append_style('label', style)

  def add_query(self, sql, geom='geom', cmin=0, cmax=1000, bins=25, key=None, label=None, cmap='Blues'):
    cmin = float(cmin)
    cmax = float(cmax)
    assert cmax > cmin
    assert cmax-cmin > 0
    
    # Create the rules and filters for the color map
    style = mapnik.Style()
    cmap = plt.get_cmap(cmap)
    for value in numpy.linspace(cmin, cmax, bins):
      color = (value-cmin) / (cmax-cmin) # (cmin-cmax)
      color = cmaprgb(cmap, color)
      rule = mapnik.Rule()
      print "filter:", key, ">", value
      rule.filter = mapnik.Filter("[%s] > %s"%(key, value))
      p = mapnik.PolygonSymbolizer(mapnik.Color(color))
      p.fill_opacity = 0.7
      rule.symbols.append(p)
      style.rules.append(rule)
    self.m.append_style('cmap', style)
    
    # Add the PostGIS layer.
    layer = mapnik.Layer('cmap')
    layer.styles.append('cmap')
    layer.datasource = mapnik.PostGIS(
      host='localhost',
      user='irees',
      password='',
      dbname='acs',
      table=sql,
      geometry_field='geom'
    )
    self.m.layers.append(layer)    

  def add_shapefile(self, filename, name, style):
    layer = mapnik.Layer(name)
    layer.datasource = mapnik.Shapefile(file=filename)
    layer.styles.append(style)
    self.m.layers.append(layer)
  
  def add_label(self, x, y, label):
    # Ughghh....!!! Doesn't seem to work :(
    # p = "POINT(%s %s)"%(x, y)
    # ds = mapnik.MemoryDatasource()
    # f = mapnik.Feature(mapnik.Context(), 1)
    # f.add_geometries_from_wkt(p)
    # ds.add_feature(f)
    # layer = mapnik.Layer('label')
    # layer.styles.append('label')
    # layer.datasource = ds
    # self.m.layers.append(layer)
    
    # Ugh. This is very ugly.
    y, x = 25.465027, -79.770770
    sql = """(SELECT ST_SetSRID(ST_Point(%(x)s, %(y)s), 4326) as geom, '%(label)s' AS name) AS ok"""%{'x':x, 'y':y, 'label':label}
    print sql
    layer = mapnik.Layer('label')
    layer.styles.append('label')
    layer.datasource = mapnik.PostGIS(
      host=cityism.config.host,
      user=cityism.config.user,
      password=cityism.config.password,
      dbname=cityism.config.dbname,
      table=sql,
      geometry_field='geom',
    )
    self.m.layers.append(layer)

  def add_xml(self, filename):
    mapnik.load_map(self.m, filename)

  def output(self, filename, lat=29.762131, lon=-95.360608, radius=100000):
    # self.m.zoom_all()
    x, y = projmerc(lat=lat, lon=lon)
    bbox = x-radius, y-radius, x+radius, y+radius
    print "bbox:", bbox
    extent = mapnik.Box2d(*bbox)
    self.m.zoom_to_box(extent)
    mapnik.render_to_file(self.m, filename)

def run(xml=None, sql=None, lat=None, lon=None, radius=None, output=None, key=None, label=None, cmin=None, cmax=None, bins=None, cmap=None):
    anim = HousingAnimation()
    if args.xml:
      anim.add_xml(args.xml)
      
    # Load the coastline
    anim.add_shapefile(COASTLINE, 'coastline', 'coastline')
    
    # Load the PostGIS data
    if args.sql:
      with open(args.sql) as f:
        sql = f.read()
      anim.add_query(sql, key=args.key, label=args.label, cmap=args.cmap, cmin=args.cmin, cmax=args.cmax, bins=args.bins)

    # Load the interstates
    anim.add_shapefile(MOTORWAYS, 'motorways', 'motorways')
    
    # Works...
    anim.add_label(lon, lat, label)
    
    if args.output:
      anim.output(args.output, lat=args.lat, lon=args.lon, radius=args.radius)
  
  
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Input
    parser.add_argument("--xml")
    parser.add_argument("--sql")
    
    # Coords
    parser.add_argument("--lat", type=float, default=29.762131)
    parser.add_argument("--lon", type=float, default=-95.360608)
    parser.add_argument("--radius", type=float, default=100000)

    # Output
    parser.add_argument("--output")
    # parser.add_argument("--nx", default=1024, type=int)
    # parser.add_argument("--ny", default=1024, type=int)

    # Color map
    parser.add_argument("--key", default="density_2000_2010")
    parser.add_argument("--label", default="2000 - 2010")
    parser.add_argument("--cmin", default=0, type=int)
    parser.add_argument("--cmax", default=1000, type=int)
    parser.add_argument("--bins", default=25, type=int)
    parser.add_argument("--cmap", default="Blues")
    args = parser.parse_args()

    args.output = "%s.png"%args.key
    run(**vars(args))
    
