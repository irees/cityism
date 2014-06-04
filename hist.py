"""Quick histogram."""
import argparse
import numpy

import psycopg2.extras
import matplotlib.pyplot as plt

import cityism.config

# I should just get the colorbrewers library
COLORS = {
    'divergent_10': [
        '#b32448', # The default is a little too strong for my tastes. '#9e0142'
        '#d53e4f',
        '#f46d43',
        '#fdae61',
        '#fee08b',
        '#e6f598',
        '#abdda4',
        '#66c2a5',
        '#3288bd',
        '#5e4fa2' 
    ],
    'sequential_9': [
        '#ffffd9',
        '#edf8b1',
        '#c7e9b4',
        '#7fcdbb',
        '#41b6c4',
        '#1d91c0',
        '#225ea8',
        '#253494',
        '#081d58'
    ],
    'sequential_5': [
        '#f1eef6',
        '#bdc9e1',
        '#74a9cf',
        '#2b8cbe',
        '#045a8d'
    ]
}

def filterkey(items, key, minvalue=None):
    """Filter objects by key"""
    if minvalue is not None:
        return [i for i in items if i.get(key) > minvalue]
    return [i for i in items if i.get(key)]


def histogram(values, bins=50, weights=None, density=False):
    """Display matpotlib histogram."""
    values = filter(None, values)
    hist, bins = numpy.histogram(values, bins=bins, weights=weights, density=density)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2
    plt.bar(center, hist, align='center', width=width)
    plt.show()            

def histocarto(bins, key, colors):
    """Generate CartoCSS useful for Tilemill. And a legend."""
    fmt_cartocss = """  [%(key)s > %(bmin)s]{ polygon-fill: %(color)s; line-color: %(color)s; }"""
    fmt_legend =   """    <li><span style="background:%(color)s;"></span>%(min)s</li>"""
    for b, color in zip(bins, colors):
        print fmt_cartocss%{
            'key': key,
            'bmin': b[1],
            'bmax': b[2],
            'color': color
        }
    for b, color in zip(bins, colors):
        print fmt_legend%{
            'color': color,
            'min': round(b[1], 2)
        }
        
def binstats(bins, key, metric):
    total_bin = sum(i[3] for i in bins)
    total = sum([i.get(metric) for i in items])
    print "Total bins: %s"%len(bins)
    print "Bin metric total:", total_bin
    print "Difference:", total - total_bin
    for bin in bins:
        print "min:", bin[1], "max:", bin[2], "pop:", sum(i.get('pop') for i in bin[5]), "aland:", sum(i.get('aland') for i in bin[5])/1e6
    
def breaks(items, key='hdi', metric='pop', count=10):
    """Break a list of dicts into ranges."""
    # TODO: Use numpy.interpolate
    
    # This function is somewhat buggy and needs work :(
    # I should ask a real statistician how to do this.
    # numpy has a great percentile method, but doesn't do weights.
    items = filterkey(items, key, minvalue=0)
    items = filterkey(items, metric, minvalue=0)
    total = sum([i.get(metric) for i in items])
    width = total / float(count)

    # Don't ask... 
    # I can choose to have the highest or the lowest decile
    # more closely match the desired width. In most cases,
    # I'm more interested in the highest decile -- so, reverse.
    i = 0 
    bins = []
    items = sorted(items, key=lambda x:x.get(key), reverse=True)
    for c in range(count-1, -1, -1):
        refs = []
        t = 0
        start = items[i].get(key)
        while t <= width:
            t += items[i].get(metric)
            refs.append(items[i])
            if i+1 >= len(items):
                break
            i += 1
        end = items[i].get(key)
        bin = (c, end, start, t, t/width, refs)
        bins.append(bin)
    bins.reverse()    
    return bins

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bins", help="Bins", default=10, type=int)
    parser.add_argument("--colors", help="Color scheme", default="divergent_10")
    parser.add_argument("--mult", help="Key factor (e.g. convert km^2 density to mi^2 = 2.58999)", default=1.0, type=float)    
    parser.add_argument("--key", help="Histogram column", default='hdi')
    parser.add_argument("--outkey", help="Output key", default=None)
    parser.add_argument("--metric", help="Bin metric", default='pop')
    args = parser.parse_args()    

    args.outkey = args.outkey or args.key

    items = []
    with cityism.config.connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """SELECT * FROM result_hdi;"""
            cursor.execute(query)
            for row in cursor:
                row = dict(row)
                row.pop('geom', None)
                if row.get(args.key):
                    row[args.key] = row[args.key] * args.mult
                items.append(row)

    bins = breaks(items, count=args.bins, key=args.key, metric=args.metric)
    binstats(bins=bins, key=args.key, metric=args.metric)
    histocarto(bins=bins, key=args.outkey, colors=COLORS[args.colors])

