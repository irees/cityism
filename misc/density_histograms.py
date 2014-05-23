"""Distribution of population densities."""

import argparse
import itertools
import collections
import numpy as np
import matplotlib.pyplot as plt
import psycopg2.extras
import cityism.config
import cityism.acs
from cityism.utils import *

# Big city geoids.
# Houston 4835000
# Dallas 4819000
# Los Angeles 0644000
# San Francisco 0667000
# NYC 3651000
# Austin 4805000
# Chicago 1714000
# Philadelphia 4260000
# Washington DC 1150000
# Boston 2507000
# Phoenix 0455000

def plot(items, norm=True):
    # This is ugly. Don't look.
    # Filter
    items = [i for i in items if i.get('pop_dmi')]

    # Group
    groups = collections.defaultdict(list)
    for i in items:
        groups[i.get('label')].append(i)
    
    # Plot
    fig, ax = plt.subplots()
    # ax.set_xticks(np.arange(0, 1000000, 20000), minor=False)
    # ax.set_yticks(np.arange(0, 10000000, 500000), minor=False)

    # Setup the colors
    NUM_COLORS = len(groups)
    cm = plt.get_cmap('gist_rainbow')
    cm = itertools.cycle([cm(1.*i/NUM_COLORS) for i in range(NUM_COLORS)])
    
    ax.xaxis.grid(True, which='major')
    ax.yaxis.grid(True, which='major')
    plt.title("Population density distributions of selected cities\n(Tracts, ACS 5-year 2012)")
    plt.ylabel("Population above density threshold")
    plt.xlabel("Population density (people/sq.mi)")
    plt.grid(True)
    
    labeloffset = 0.0
    if norm:
      labeloffset = -0.1

    for label, c in groups.items():
        print "\n=====", label, len(c)

        x, y = [], []
        pop_total = float(sum(i.get('pop') for i in c))

        if norm:
          pop_div, pop_max = pop_total, 1.0
        else:
          pop_div, pop_max = 1.0, pop_total
        t = 0.0
        for i in sorted(c, key=lambda x:x.get('pop_dmi'), reverse=True):
            x.append(i.get('pop_dmi'))
            y.append(t / pop_div)
            t += i.get('pop')

        x.append(0)
        y.append(pop_max)
        color = cm.next()

        # label = "%s (%s)"%(label, int(midpoint))
        print "Total population:", pop_total
        print "X:"
        print x
        print "Y:"
        print y

        # Plot
        plt.plot(x, y, label=label, color=color)

        # Label
        yoffset = (pop_max/2)+labeloffset
        midpoint = np.interp([yoffset], y, x)[0]
        plt.text(midpoint, yoffset, label, color=color)
        if norm:
          labeloffset += 0.05
    
    # plt.legend(loc=1)
    plt.show()
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--norm", help="Normalize city populations", action="store_true")
    parser.add_argument("places", nargs="*")
    args = parser.parse_args()    
    PLACES = tuple(args.places)
    items = []
    query = """
        SELECT
        	tiger.geoid AS tiger_geoid,
            tiger.aland,
        	place.geoid AS place_geoid,
        	place.name AS label,
        	acs_b01001.b01001_001 as pop,
        	acs_b01001.b01001_001/tiger.aland*1e6*2.58999 AS pop_dmi
        FROM
        	place_2012 AS place,
        	tract_2012 AS tiger
        INNER JOIN
        	acs_b01001 ON acs_b01001.geoid = tiger.geoid
        WHERE
        	place.geoid IN %(places)s AND
        	tiger.aland > 0 AND
        	ST_Contains(place.geom, ST_SetSRID(ST_MakePoint(to_number(tiger.intptlon, 'S999D999999'), to_number(tiger.intptlat, 'S99D999999'), 4269), 4326)); 
    """
    with cityism.config.connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            print cursor.mogrify(query, {'places':PLACES})
            cursor.execute(query, {'places':PLACES})
            for row in cursor:
                row = dict(row)
                items.append(row)
                
    plot(items, norm=args.norm)

