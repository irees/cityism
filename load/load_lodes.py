"""Load data from LODES employment data into SQL."""
import argparse
import csv
import sys
import collections
import cityism.config

def parse_lodes(filename, tract=False):
  ret = {}
  with open(filename) as f:
    reader = csv.reader(f)
    header = reader.next()
    headers = ['lodes_%s'%i.lower() for i in header[1:-1]]
    for row in reader:
      geoid = row[0]
      data = map(int, row[1:-1])
      if tract:
        geoid = geoid[:-4]
      if geoid not in ret:
        ret[geoid] = collections.defaultdict(int)
        ret[geoid]['geoid'] = geoid
      for k,v in zip(headers, data):
        ret[geoid][k] += v
  
  s = 0
  for v in sorted(ret.values(), key=lambda x:x.get('lodes_c000')):
    print v['geoid'], v['lodes_c000']
    s += v['lodes_c000']
  print s
  return ret, sorted(headers)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", help="filename")
  parser.add_argument("--tract", help="Aggregate by tract", action="store_true")
  args = parser.parse_args()

  data, headers = parse_lodes(args.filename, tract=args.tract)

  query_lodes_create = """
    CREATE TABLE IF NOT EXISTS lodes_wac (
    	geoid VARCHAR NOT NULL PRIMARY KEY,
        %(columns)s
    );
    """%{
    'columns': ','.join(['%s INTEGER'%i for i in headers]),
  }

  query_lodes_insert = """
   INSERT INTO lodes_wac
   VALUES (
       %%(geoid)s,
       %(columns)s
      )
  """%{
    'columns': ','.join(['%%(%s)s'%i for i in headers])
  }

  with cityism.config.connect() as conn:
    with conn.cursor() as cursor:
      print cursor.execute(query_lodes_create)    
      for tract in data.values():
        print "%s..."%tract['geoid']
        print cursor.execute(query_lodes_insert, tract)

  
if __name__ == "__main__":
    main()
  