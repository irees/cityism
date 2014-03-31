import numpy
import cityism.acs
from hist import *

# CALIFORNIA = 06
# Alameda = 001
# Contra Costa = 013
# San Francisco = 075
# San Mateo = 081
# Napa = 055
# Marin = 041
# Santa Clara = 085
# Santa Cruz = 087
# Solano = 095
# Sonoma = 097

counties = ['001', '013', '075', '081', '055', '041', '085', '087', '095', '097']
kmsm = 0.386102

def main():
    ret = []
    with cityism.config.connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """SELECT * FROM result_hdi WHERE statefp = %(statefp)s;"""
            cursor.execute(query, {'statefp':'06'})
            for row in cursor:
                row = dict(row)
                row.pop('geom', None)
                row['density'] = (row['pop'] / row['aland']) * 1e6 / kmsm
                ret.append(row)                
    return ret

ret = []
if __name__ == "__main__":
    items = main()
    for countyfp in counties:
        c = cityism.acs.ACSFips.ANSI_STATES_COUNTIES.get(('06', countyfp))
        citems = filter(lambda x:x.get('countyfp')==countyfp, items)
        print "\n======== County:", countyfp, c
        # densitystats(ret, countyfp=countyfp)
        total_pop = sum(i.get('pop') for i in citems)
        total_aland = sum(i.get('aland') for i in citems)
        print "Population:", total_pop
        print "Land area:", total_aland / 1e6 * kmsm
        print "Overall density:", (total_pop / total_aland) * 1e6
        breaks(citems, key='density', metric='pop')
        