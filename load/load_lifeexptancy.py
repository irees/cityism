import csv
import os
import sys

import psycopg2
import psycopg2.extras

import config

def parse(filename):
    ret = []
    with open(filename) as f:
        reader = csv.reader(f)
        header = reader.next()
        for row in reader:
            fips = '%05d'%(int(row[0]))
            state = fips[:2]
            county = fips[2:5]
            year = row[3]
            if year == '2009':
                print state, county, row[4]
                ret.append([state, county, float(row[4])])
    return ret
    
if __name__ == "__main__":
    ret = parse(sys.argv[1])
    query_create = """
        CREATE TABLE IF NOT EXISTS data_life_expectancy (
              statefp character varying(2),
              countyfp character varying(3),
              value float,
              PRIMARY KEY(statefp, countyfp)
          );
    """
    query_insert = """
        INSERT INTO data_life_expectancy VALUES (%(statefp)s, %(countyfp)s, %(value)s);
    """


    with cityism.config.connect() as conn:
        cur = conn.cursor()
        cur.execute(query_create)
        for statefp, countyfp, value in ret:
            cur.execute(query_insert, {'statefp':statefp, 'countyfp':countyfp, 'value':value})
