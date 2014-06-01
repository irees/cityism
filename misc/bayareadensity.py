import csv
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

BAY_AREA_COUNTIES = ['001', '013', '075', '081', '055', '041', '085', '087', '095', '097']
# Los Angeles counties
LA_COUNTIES = ['037']
kmsm = 0.386102

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="Histogram column", default='hdi')
    parser.add_argument("--metric", help="Bin metric", default='pop')
    parser.add_argument("--bins", help="Bins", default=10, type=int)
    parser.add_argument("--county", help="County. Can be specified multiple times. Default is 9 Bay Area Counties", action='append')
    parser.add_argument("outfile", help="CSV output file", nargs='?')
    args = parser.parse_args()    

    counties = args.county or BAY_AREA_COUNTIES
    print "COUNTIES?", counties

    items = []
    with cityism.config.connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """SELECT * FROM result_hdi WHERE statefp = %(statefp)s;"""
            cursor.execute(query, {'statefp':'06'})
            for row in cursor:
                row = dict(row)
                row.pop('geom', None)
                # ... convert to sq. mi. to simplify things.
                row['aland'] = row['aland'] / 1e6 * kmsm
                row['density'] = (row['pop'] / row['aland']) 
                items.append(row)                
    
    if args.outfile:
        with open(args.outfile, 'wb') as csvfile:
            for countyfp in counties:
                citems = filter(lambda x:x.get('countyfp')==countyfp, items)
                bins = breaks(citems, key=args.key, metric=args.metric, count=args.bins)
                total_pop = sum(i.get('pop') for i in citems)
                total_aland = sum(i.get('aland') for i in citems) 
                c = cityism.acs.ACSFips.ANSI_STATES_COUNTIES.get(('06', countyfp))
                writer.writerow(["County:", countyfp, c])
                writer.writerow(["Population:", int(total_pop)])
                writer.writerow(["Land area (sq. mi):", '%0.2f'%total_aland])
                writer.writerow(["Overall density:", int(total_pop/total_aland)])
                writer.writerow(["decile", "density_min", "density_max", "pop", "aland", "# tracts", "tracts"])
                for bin in bins:
                    aland = sum(i.get('aland') for i in bin[5])
                    tracts = ", ".join(i.get('name') for i in bin[5])
                    writer.writerow([bin[0], int(bin[1]), int(bin[2]), int(bin[3]), '%0.2f'%aland, len(bin[5]), tracts])
                writer.writerow([])
