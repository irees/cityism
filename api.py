import argparse
import collections
import csv
import json
import os
import sys
import inspect
import shapefile
import acs
import math

import psycopg2

import config

CITIES = {
    'Houston': (29.7573869124592, -95.3631898316691),
    'Dallas': (32.779411, -96.806802),
    'Austin': (30.268035, -97.745333),
    'San Antonio': (29.424761, -98.493591),
    'Lubbock': (33.585527, -101.845632),
    'Galveston': (29.299392, -94.794328)
}

class Query(object):
    def __init__(self):
        pass

    def query(self):
        pass

class QueryACSTitle(Query):
    pass


def acstitle(acstable=None, conn=None):
    query = """
        SELECT acstable, title, subject FROM acsmeta where acstable = %(acstable)s;
    """
    with conn.cursor() as cursor:
        params = {'acstable':acstable}
        cursor.execute(query, params)
        row = cursor.fetchone()
    return row[2]
    
def radial(city=None, x=None, y=None, acstable='B25034', radius_inner=0, radius_outer=1000, conn=None, density=True):
    query = """
        WITH 
            cupcake AS ( SELECT 
                utmzone(ST_SetSRID(ST_MakePoint(%%(x)s, %%(y)s), 4269)) AS srid,
                ST_Difference(
                        ST_Buffer_Meters(ST_SetSRID(ST_MakePoint(%%(x)s, %%(y)s), 4269), %%(radius_outer)s),
                        ST_Buffer_Meters(ST_SetSRID(ST_MakePoint(%%(x)s, %%(y)s), 4269), %%(radius_inner)s)
                ) AS donut
            )
        SELECT 
            tracts.geoid,
            ST_Area(ST_Transform(ST_Intersection(tracts.geom, cupcake.donut), cupcake.srid)) AS area_intersect,
            ST_Area(ST_Transform(tracts.geom, cupcake.srid)) AS area_tract,
            acs_%(acstable)s.*
        FROM
            cupcake,
            tracts
        INNER JOIN
            acs_%(acstable)s ON tracts.geoid = acs_%(acstable)s.geoid
        WHERE
            ST_Intersects(
                tracts.geom,
                cupcake.donut
            );
    """%{'acstable':acstable}
    
    if city:
        y,x = CITIES[city]
    if x is None or y is None:
        raise Exception("Need x, y coords.")
    
    if not acstable:
        raise Exception("No ACS table given.")
        
    if radius_inner > radius_outer:
        radius_inner = radius_outer
    if radius_outer > 100000:
        raise Exception("Max 100km.")
    if radius_inner < 0:
        raise Exception("Min 0km.")
    
    plot = []
    params = {'radius_outer':radius_outer, 'radius_inner':radius_inner, 'x':x, 'y':y}        

    print "-------------"
    print query%params
    
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        return []
    
    area = 0
    data = []
    for row in rows:
        print row
        pct = row[1] / row[2]
        data.append([i*pct for i in row[4:]])
        area += row[1]

    # The buffers are not perfect circles, so sum of intersected area
    #   will be slightly less than expected.
    # print "Total area?", area, "expected:", math.pi*(radius_outer)**2 - math.pi*(radius_inner)**2
    
    plot = []
    for count, i in enumerate(zip(*data)):
        total = sum(i)
        if density:
            total /= (area / 1e6)
        plot.append(total)        

    return plot
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--acstable", help="ACS Table")
    parser.add_argument("--x", help="X", type=float)
    parser.add_argument("--y", help="Y", type=float)
    parser.add_argument("--city", help="City")
    parser.add_argument("--start", type=int, default=1000)
    parser.add_argument("--end", type=int, default=30000)
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--density", type=bool, help="Plot density instead of counts")
    parser.add_argument("--reverse", type=bool, help="Reverse column output")
    args = parser.parse_args()
    
    plots = []
    params = acs.TABLES.get(args.acstable).getchildren()
    kwargs = dict(
        city=args.city,
        acstable=args.acstable,
        density=args.density
    )

    with config.connect() as conn:
        print args.start, args.end, args.width
        for radius in range(args.start, args.end, args.width):
            plot = radial(city=args.city, acstable=args.acstable, radius_inner=radius, radius_outer=radius+args.width, conn=conn)
            plots.append(plot)

    # # Ugly, dirty csv. Fix me.
    if args.reverse: params.reverse()
    print "Radial distribution query:"
    print "\t" + "\t".join(i.title for i in params)
    for count, row in enumerate(plots):
        if args.reverse: row.reverse()
        print "%s\t"%(count) + "\t".join('%0.3f'%i for i in row)
        
        
    