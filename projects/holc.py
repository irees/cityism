import argparse
import numpy

import psycopg2.extras
import cityism.config

# CREATE TABLE holc (ogc_fid integer, name varchar, description varchar, category varchar); SELECT AddGeometryColumn('holc', 'geom', 4326, 'POLYGON', 3);
# INSERT INTO holc (ogc_fid, name, description, geom, category) SELECT ogc_fid, name, description, ST_Buffer(wkb_geometry,0.0), 'a' as category FROM "area a";
# INSERT INTO holc (ogc_fid, name, description, geom, category) SELECT ogc_fid, name, description, ST_Buffer(wkb_geometry,0.0), 'b' as category FROM "area b";
# INSERT INTO holc (ogc_fid, name, description, geom, category) SELECT ogc_fid, name, description, ST_Buffer(wkb_geometry,0.0), 'c' as category FROM "area c";
# INSERT INTO holc (ogc_fid, name, description, geom, category) SELECT ogc_fid, name, description, ST_Buffer(wkb_geometry,0.0), 'd' as category FROM "area d";
#
# CREATE TABLE tracts_holc AS (
#   SELECT
#     tracts.geoid10,
#     ST_Area(tracts.geom) as tracts_area,
#     SUM(ST_Area(ST_Intersection(tracts.geom, holc.geom))) as holc_area,
#     SUM(CASE WHEN holc.category = 'a' THEN ST_Area(ST_Intersection(tracts.geom, holc.geom)) ELSE 0 END) as holc_a,
#     SUM(CASE WHEN holc.category = 'b' THEN ST_Area(ST_Intersection(tracts.geom, holc.geom)) ELSE 0 END) as holc_b,
#     SUM(CASE WHEN holc.category = 'c' THEN ST_Area(ST_Intersection(tracts.geom, holc.geom)) ELSE 0 END) as holc_c,
#     SUM(CASE WHEN holc.category = 'd' THEN ST_Area(ST_Intersection(tracts.geom, holc.geom)) ELSE 0 END) as holc_d
#   FROM
#     tracts,
#     holc
#   WHERE
#     ST_Intersects(tracts.geom, holc.geom)
#   GROUP BY
#     tracts.gid);

query = """
SELECT 
  -- tracts.geom,
  tracts_holc.geoid10, 
  b02001_001 as pop_total, 
  b02001_002 as pop_white, 
  b02001_003 as pop_black, 
  holc_a/holc_area, 
  holc_b/holc_area, 
  holc_c/holc_area, 
  holc_d/holc_area, 
  (holc_a*1.0+holc_b*0.666+holc_c*0.333+holc_d*0)/holc_area as holc_score 
FROM 
  tracts_holc 
INNER JOIN 
  acs_b02001 on acs_b02001.geoid = tracts_holc.geoid10
INNER JOIN
  tracts on tracts.geoid10 = tracts_holc.geoid10
WHERE
  holc_area/tracts_area > 0.2 AND tracts.countyfp10 = '001';
"""

# 3288BD - blue
# ABDDA4 - green
# FEE08B - yellow
# F46D43 - red

if __name__ == "__main__":
  items = []
  with cityism.config.connect() as conn:
      with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
          print cursor.mogrify(query)
          cursor.execute(query)
          for row in cursor:
              row = dict(row)
              items.append(row)
              
  print items
  import numpy as np
  import matplotlib.pyplot as plt
  x = [i.get('holc_score', 0) for i in items]
  y = [i.get('pop_white', 0)/float(i.get('pop_total', 0)) for i in items]
  # area = np.pi * np.array([i.get('pop_total',0)/1000 for i in items])**2
  plt.scatter(x, y) # s=area)
  plt.title('Alameda County')
  plt.xlabel('Home Owners Loan Corp. Category (1937; 1.0 = green; 0.0 = red)')
  plt.ylabel('Population Percent White Alone (2012; American Community Survey, Table B02001)')
  plt.xlim(-0.05,1.05)
  plt.ylim(-0.05,1.05)
  plt.show()
  
  
  
  