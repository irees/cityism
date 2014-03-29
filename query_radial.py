"""Radial query."""
import math
import argparse

import acs
import config
import query

class QueryRadial(cityism.query.Query):
    def query(self, city=None, x=None, y=None, acstable='B25034', radius_inner=0, radius_outer=1000, density=True, level='tracts'):
        if level not in ['tracts', 'blocks', 'counties']:
            raise Exception("Invalid level")
        
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
                %(level)s.geoid,
                ST_Area(ST_Transform(ST_Intersection(%(level)s.geom, cupcake.donut), cupcake.srid)) AS area_intersect,
                ST_Area(ST_Transform(%(level)s.geom, cupcake.srid)) AS area_tract,
                acs_%(acstable)s.*
            FROM
                cupcake,
                %(level)s
            INNER JOIN
                acs_%(acstable)s ON %(level)s.geoid = acs_%(acstable)s.geoid
            WHERE
                ST_Intersects(
                    %(level)s.geom,
                    cupcake.donut
                );
        """%{'acstable':acstable, 'level':level}
    
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
        data = []
        area = 0
        params = {'radius_outer':radius_outer, 'radius_inner':radius_inner, 'x':x, 'y':y}        
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
    parser.add_argument("--x", help="X", type=float)
    parser.add_argument("--y", help="Y", type=float)
    parser.add_argument("--level", help="Census geography level", default="tracts")
    parser.add_argument("--city", help="City")
    parser.add_argument("--start", type=int, default=1000)
    parser.add_argument("--end", type=int, default=30000)
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--density", type=bool, help="Plot density instead of counts")
    parser.add_argument("--reverse", type=bool, help="Reverse column output")
    args = parser.parse_args()
    
    plots = []
    with cityism.config.connect() as conn:
        for radius in range(args.start, args.end, args.width):
            plot = QueryRadial(conn=conn).query(city=args.city, acstable=args.acstable, radius_inner=radius, radius_outer=radius+args.width, level=args.level)
            plots.append(plot)

    # Ugly, dirty csv. Fix me.
    params = cityism.acs.ACSMeta.get(args.acstable).getchildren()
    if args.reverse:
        params.reverse()
    print "Radial distribution query:"
    print "\t" + "\t".join(i.title for i in params)
    for count, row in enumerate(plots):
        if args.reverse: row.reverse()
        print "%s\t"%(count) + "\t".join('%0.3f'%i for i in row)
        
