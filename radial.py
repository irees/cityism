"""Radial query."""
import math
import argparse
import csv
import sys

import acs
import config
import query

class QueryRadial(query.Query):
    def query(self, lon=None, lat=None, acstable='B25034', radius_inner=0, radius_outer=1000, density=True, level='tract'):
        query = """
            WITH
                cupcake AS ( SELECT
                    utmzone(ST_SetSRID(ST_MakePoint(%%(lon)s, %%(lat)s), 4326)) AS srid,
                    ST_Difference(
                            ST_Buffer_Meters(ST_SetSRID(ST_MakePoint(%%(lon)s, %%(lat)s), 4326), %%(radius_outer)s),
                            ST_Buffer_Meters(ST_SetSRID(ST_MakePoint(%%(lon)s, %%(lat)s), 4326), %%(radius_inner)s)
                    ) AS donut
                )
            SELECT
                geo.geoid,
                ST_Area(ST_Transform(ST_Intersection(geo.geom, cupcake.donut), cupcake.srid)) AS area_intersect,
                ST_Area(ST_Transform(geo.geom, cupcake.srid)) AS area_tract,
                acs_%(acstable)s.*
            FROM
                cupcake,
                %(level)s AS geo
            INNER JOIN
                acs_%(acstable)s ON geo.geoid = acs_%(acstable)s.geoid
            WHERE
                ST_Intersects(
                    geo.geom,
                    cupcake.donut
                );
        """%{'acstable':acstable, 'level':level}

        if lon is None or lat is None:
            raise Exception("Need lon, lat.")

        if not acstable:
            raise Exception("No ACS table given.")

        if radius_inner > radius_outer:
            radius_inner = radius_outer
        if radius_outer > 100000:
            raise Exception("Max 100km.")
        if radius_inner < 0:
            raise Exception("Min 0km.")

        plot = []
        data = []
        area = 0
        params = {'radius_outer':radius_outer, 'radius_inner':radius_inner, 'lon':lon, 'lat':lat}
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            for row in cursor:
                pct = row[1] / row[2]
                data.append([i*pct for i in row[4:]])
                area += row[1]

        # The buffers are not perfect circles, so sum of intersected area
        #     will be slightly less than expected.
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
    parser.add_argument("--lon", help="Longitude", type=float)
    parser.add_argument("--lat", help="Latitude", type=float)
    parser.add_argument("--level", help="Census geography level", default="tract")
    parser.add_argument("--start", type=int, default=1000)
    parser.add_argument("--end", type=int, default=50000)
    parser.add_argument("--width", type=int, default=1000)
    args = parser.parse_args()

    plots = []
    with config.connect() as conn:
        for radius in range(args.start, args.end, args.width):
            plot = QueryRadial(conn=conn).query(acstable=args.acstable, radius_inner=radius, radius_outer=radius+args.width, level=args.level, lon=args.lon, lat=args.lat)
            plots.append(plot)

    # Ugly, dirty csv. Fix me.
    params = acs.ACSMeta.get(args.acstable).getchildren()
    writer = csv.writer(sys.stdout)
    writer.writerow(['Radial distribution query:'])
    writer.writerow(['lon',args.lon])
    writer.writerow(['lat',args.lat])
    writer.writerow(['geography',args.level])
    writer.writerow(['width',args.width])
    writer.writerow([])
    writer.writerow(['']+[i.title for i in params])
    for count, row in enumerate(plots):
      writer.writerow([count]+['%0.3f'%i for i in row])
