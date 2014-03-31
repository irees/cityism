"""Quick histogram."""
import numpy
import matplotlib.pyplot as plt
import psycopg2.extras
import cityism.config
from cityism.utils import *

colors_diverge_11 = [
    '#9e0142',
    '#d53e4f',
    '#f46d43',
    '#fdae61',
    '#fee08b',
    '#ffffbf',
    '#e6f598',
    '#abdda4',
    '#66c2a5',
    '#3288bd',
    '#5e4fa2'
]
colors_diverge_10 = [
    '#9e0142',
    '#d53e4f',
    '#f46d43',
    '#fdae61',
    '#fee08b',
    '#e6f598',
    '#abdda4',
    '#66c2a5',
    '#3288bd',
    '#5e4fa2'
]

def histocarto(key, bins, colors):
    """Generate CartoCSS useful for Tilemill. And a legend."""
    ret_cartocss = []
    ret_legend = []
    fmt_cartocss = """  [%(key)s > %(bmin)s][%(key)s <= %(bmax)s]{ polygon-fill: %(color)s; line-color: %(color)s; }"""
    fmt_legend = """    <li><span style="background:%(color)s;"></span>%(min)s</li>"""
    for b,color in zip(bins, colors):
        ret_cartocss.append(fmt_cartocss%{
            'key': key,
            'bmin': b[1],
            'bmax': b[2],
            'color': color
        })
        ret_legend.append(fmt_legend%{
            'color': color,
            'min': round(b[1], 2)
        })
    print "\n".join(ret_legend)
    print "\n".join(ret_cartocss)
    
def histogram(values, bins=50, weights=None, density=False):
    """Display matpotlib histogram."""
    values = filter(None, values)
    hist, bins = numpy.histogram(values, bins=bins, weights=weights, density=density)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2
    plt.bar(center, hist, align='center', width=width)
    plt.show()            

def breaks(items, count=10, key='hdi', metric='pop'):
    """Break a list of dicts into ranges."""
    # This function is somewhat buggy and needs work :(
    items = filterkey(items, key, minvalue=0)
    items = filterkey(items, metric, minvalue=0)
    items = sorted(items, key=lambda x:x.get(key))
    
    print "Splitting key %s into %s bins using metric %s"%(key, count, metric)
    total = sum([i.get(metric) for i in items])
    width = total / float(count)
    print "total metric:", total
    print "width?", width

    i = 0 
    bins = []
    for c in range(count):
        t = 0
        start = items[i].get(key)
        while t <= width:
            t += items[i].get(metric)
            if i+1 >= len(items):
                break
            i += 1

        end = items[i].get(key)
        bin = (c, start, end, t)
        print bin
        bins.append(bin)

    print "leftovers?"
    print i, len(items)
    
    total_bin = sum(i[3] for i in bins)
    print "Total bins: %s"%len(bins)
    print "Bin metric total:", total_bin
    print "Difference:", total - total_bin
    return bins

def main():
    ret = []
    with cityism.config.connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """SELECT * FROM result_hdi;"""
            cursor.execute(query)
            for row in cursor:
                row = dict(row)
                row.pop('geom', None)
                ret.append(row)
        for row in ret: 
            print row.get('geoid'), row.get('hdi'), row.get('pop')
        bins = breaks(ret, count=10, key='hdi', metric='pop')
        print histocarto(key='hdi', bins=bins, colors=colors_diverge_10)
    return ret

ret = []
if __name__ == "__main__":
    ret = main()
    # E.g. in interactive mode:
    # histogram((i.get('hdi') for i in ret))
    