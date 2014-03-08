import argparse
import acs
import config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", help="Year", default=2012)
    parser.add_argument("--span", help="Span", default=5)
    parser.add_argument("--state", help="State", default='tx')
    parser.add_argument("--acstable", help="ACS Table")
    args = parser.parse_args()

    acstable = acs.TABLES.get(args.acstable)
    acstables = acstable.getchildren()

    c = acs.ACSParser(acstable=args.acstable, year=args.year, span=args.span, state=args.state)
    tracts = c.load()

    query_acs_create = """
    CREATE TABLE IF NOT EXISTS acs_%(acstable)s (
    	geoid VARCHAR NOT NULL PRIMARY KEY,
        %(columns)s
    );"""%{
        'acstable':acstable.acstable,
        'columns':','.join(['%s INTEGER'%i.acstable for i in acstables]),
    }
    
    query_acs_insert = """
         INSERT INTO acs_%(acstable)s 
         VALUES (
             %%(geoid)s,
             %(acstables)s
            )
    """%{
        'acstable':acstable.acstable,
        'acstables':','.join(['%%(%s)s'%i.acstable for i in acstables])
    }
    
    print query_acs_create
    print query_acs_insert
    
    with config.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query_acs_create)    
            for tract in tracts:
                print "%s..."%tract.geoid
                cursor.execute(query_acs_insert, tract.data)

if __name__ == "__main__":
    main()
