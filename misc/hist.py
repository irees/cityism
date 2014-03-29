import numpy

import matplotlib.pyplot as plt

import cityism.config

ret = []
with cityism.config.connect() as conn:
    with conn.cursor() as cursor:
        query = """
            SELECT hdi, pop FROM result_hdi;
        """
        cursor.execute(query)
        for row in cursor:
            if row[0] and row[1]:
                ret.append(row)
            
# hist, bins = numpy.histogram(ret, bins=50, weights=pop)
# width = 0.7 * (bins[1] - bins[0])
# center = (bins[:-1] + bins[1:]) / 2
# plt.bar(center, hist, align='center', width=width)
# plt.show()            
count = 10
ret = sorted(ret)
total_pop = sum([i[1] for i in ret])
print "total population:", total_pop
width = total_pop // count
print "width?", width


i = 0 
bins = []
for c in range(count):
    t = 0
    start = ret[i][0]
    while t < width:
        t += ret[i][1]
        if i+1 >= len(ret):
            break
        i += 1

    end = ret[i][0]
    bin = (c, start, end, t)
    print bin
    bins.append(bin)
    
print "Bins?", len(bins)
bin_pop = sum(i[3] for i in bins)
print "sum bin pop:", bin_pop
print "diff?", total_pop - bin_pop
