
query = """select tract.geoid, tract.intptlat, tract.intptlon, lodes_wac.lodes_c000, acs_b01001.b01001_001 from tract_2012 as tract INNER JOIN acs_b01001 ON acs_b01001.geoid = tract.geoid INNER JOIN lodes_wac ON lodes_wac.geoid = tract.geoid WHERE tract.statefp='06';"""

base = {
    "properties": {
        "schema": {
            "census": {
                "type": "Category"
            },
            "census:jobs": {
                "type": "Attribute"
            },
            "census:pop": {
                "type": "Attribute"
            }
        }
    },
    "type": "FeatureCollection",
    "features": [],
}

import cityism.config
import psycopg2.extras 
import json

with cityism.config.connect() as conn:
  with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
    cursor.execute(query)
    for row in cursor:
      f = {}
      f['type'] = 'Feature'
      f['geometry'] = {'type': 'Point', 'coordinates':[float(row['intptlon']), float(row['intptlat'])]}
      f['id'] = row['geoid']
      f['properties'] = {'structured':{'census':{'pop':row['b01001_001'], 'jobs':row['lodes_c000']}}}
      base['features'].append(f)

print json.dumps(base)


