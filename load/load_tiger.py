"""Load TIGER shapefiles."""
import sys
import argparse
import subprocess

def psql_pipe(cmd, database='irees'):
    psqlcmd = ['psql', '-d', database]
    print psqlcmd
    print cmd
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(psqlcmd, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    print p2.communicate()[0]

class ShapeLoader(object):
    def __init__(self, table, database='irees', srid_in=4269, srid_out=4326):
        self.database = database
        self.table = table
        self.srid_in = srid_in
        self.srid_out = srid_out
        
    def drop_table(self):
        psql_pipe(["echo", "DROP TABLE %s"%self.table], database=self.database)
        
    def create_table(self, filename):
        cmd = ['shp2pgsql', '-W', 'LATIN1', '-p', '-I', '-s %s:%s'%(self.srid_in, self.srid_out), filename, self.table]
        psql_pipe(cmd, database=self.database)
    
    def load_shp(self, filename):
        cmd = ['shp2pgsql', '-W', 'LATIN1', '-s %s:%s'%(self.srid_in, self.srid_out), '-a', filename, self.table]
        psql_pipe(cmd, database=self.database)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--srid_in", help="Input SRID", default=4269)
    parser.add_argument("--srid_out", help="Input SRID", default=4326)
    parser.add_argument("table", help="Table")
    parser.add_argument("filenames", help="CSV output file", nargs='*')
    args = parser.parse_args()    
    
    loader = ShapeLoader(table=args.table, srid_in=args.srid_in, srid_out=args.srid_out)    
    print "Dropping table:", args.table
    loader.drop_table()
    print "Creating table:", args.table
    loader.create_table(args.filenames[0])
    for filename in args.filenames:
        print "Loading:", filename
        loader.load_shp(filename)