"""Load data from ACS tables into SQL."""
import argparse
import cityism.acs
import cityism.config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", help="Year", default=2012, type=int)
    parser.add_argument("--span", help="Span", default=5, type=int)
    parser.add_argument("--state", help="State", default='*')
    parser.add_argument("--acstable", help="ACS Table")
    args = parser.parse_args()

    year, span = args.year, args.span
    
    acstables = []
    if args.acstable:
      acstables.append(args.acstable)
    else:
      acstables = cityism.acs.INTERESTING[:]
    
    states = []
    if args.state == '*':
      states = [i.lower() for i in cityism.acs.ACSFips.STATES_ANSI.keys()]
    else:
      states = [args.state]
    
    for state in states:
      for acstable in acstables:
        print "Loading states %s table %s"%(state, acstable)
        try:
          acstable = cityism.acs.ACSMeta.get(acstable)
          tracts = acstable.read(year=year, span=span, state=state)
          children = acstable.getchildren()
        except Exception, e:
          print "Could not load!"
          print e
          continue

        query_acs_create = """
            CREATE TABLE IF NOT EXISTS acs_%(acstable)s (
            	geoid VARCHAR NOT NULL PRIMARY KEY,
                %(columns)s
            );
        """%{
            'acstable': acstable.acstable,
            'columns': ','.join(['%s INTEGER'%i.acstable for i in children]),
        }
    
        query_acs_insert = """
             INSERT INTO acs_%(acstable)s 
             VALUES (
                 %%(geoid)s,
                 %(children)s
                )
        """%{
            'acstable': acstable.acstable,
            'children': ','.join(['%%(%s)s'%i.acstable for i in children])
        }
    
        with cityism.config.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_acs_create)    
                for tract in tracts:
                    # if len(tract.geoid) < 8:
                    #    continue
                    print "%s..."%tract.geoid
                    print tract.__dict__
                    cursor.execute(query_acs_insert, tract.data)

if __name__ == "__main__":
    main()
