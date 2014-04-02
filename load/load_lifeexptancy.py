"""Load IMHE Life Expectancy Data for Counties.

Data source:
  http://ghdx.healthmetricsandevaluation.org/record/united-states-adult-life-expectancy-state-and-county-1987-2009
"""
import csv
import os
import sys

import psycopg2
import psycopg2.extras

import cityism.config

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
                # Total life expectancy is mean of male and female
                le = (float(row[4]) + float(row[5])) / 2
                row = {
                    'statefp': state,
                    'countyfp': county,
                    'le': le,
                    'le_male': row[4],
                    'le_female': row[5]
                }
                ret.append(row)
    return ret
    
if __name__ == "__main__":
    ret = parse(sys.argv[1])
    query_create = """
        DROP TABLE IF EXISTS data_life_expectancy;
        CREATE TABLE data_life_expectancy (
              statefp character varying(2),
              countyfp character varying(3),
              le float,
              le_male float,
              le_female float,
              PRIMARY KEY(statefp, countyfp)
          );
    """
    query_insert = """
        INSERT INTO data_life_expectancy VALUES (%(statefp)s, %(countyfp)s, %(le)s, %(le_male)s, %(le_female)s);
    """

    with cityism.config.connect() as conn:
        cur = conn.cursor()
        cur.execute(query_create)
        for row in ret:
            cur.execute(query_insert, row)
