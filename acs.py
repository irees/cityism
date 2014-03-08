"""American Community Survey Tools.

Author: Ian Rees, 2014.

"""

import argparse
import collections
import csv
import json
import os
import sys
import inspect
import glob

# Import TIGER Shapefiles:
# shp2pgsql -d -I -s 4269 tl_2012_48_tract.shp tracts | psql -d acs

class ACSParser(object):
    """American Community Survey data."""
    
    def __init__(self, year=2012, span=5, state='tx', acstable=None):
        """Parse ACS summary survey files."""
        self.year = year
        self.span = span
        self.state = state
        self.acstable = acstable

    def load(self):
        """Load data from the specified ACS survey summary files. Return ACSTracts."""
        # Get ACSMeta table.
        acstable = TABLES.get(self.acstable)
        
        # Load logrecno / tract ID map.
        geom = ACSGeometry(self.year, self.span, self.state)
        geom.load()

        # Load the data file.
        ret = []
        pattern = 'e%04d%01d%s%04d%03d.txt'%(self.year, self.span, self.state, acstable.seqno, 0)
        if self.state == '*':
            filenames = glob.glob(pattern)
        else:
            filenames = [pattern]
        for filename in filenames:
            print "Loading ACS data: %s"%filename
            with open(filename) as f:
                reader = csv.reader(f)
                for row in reader:                
                    tract = acstable.parse(row, geom=geom)
                    ret.append(tract)
            return ret

class ACSTract(object):
    """Census Tract / Block / Block Group."""

    logrecno = property(lambda self:self.data['logrecno'])
    geoid = property(lambda self:self.data['geoid'])
    
    def __init__(self, logrecno=None, geoid=None, data=None):
        """Base properties are logrecno and geoid. Data is dict of add'l
        props."""
        self.data = data or {}
        self.data['logrecno'] = logrecno
        self.data['geoid'] = geoid

class ACSMeta(object):
    """American Community Survey table definitions.

    This class parses the definitions of various ACS tables, specified in:
      Sequence_Number_and_Table_Number_Lookup.txt

    The ACS data contains hundreds of tables, with collectively thousands of
    columns. The data is split into many files, each with one or more column's
    worth of tables. The table definitions specify which file number (sequence
    number), how many columns are in a table (cells), and column number
    (seqstart+lineno) where each value can be found. The definitions also
    contain human readable descriptions of table subject area (subject) and
    description of each column (title).
    
    For example, "B25034" is a table with the title "YEAR STRUCTURE BUILT" in
    the subject "Housing". The sequence number is 104, with 10 columns
    starting at column #7. The values in these columns represent the periods
    "total", "pre 1939", "1940-1949", "1950-1959", etc.
    """
    # ACS Table Meta file layout.
    # ['File ID', 'Table ID', 'Sequence Number', 'Line Number', 'Start Position', 'Total Cells in Table', 'Total Cells in Sequence', 'Table Title',          'Subject Area']
    # ['ACSSF',   'B25034',   '0104',            ' ',           '7',              '10 CELLS',             ' ',                       'YEAR STRUCTURE BUILT', 'Housing']
    
    # Class attr
    acstables = {}
    loaded = False

    # Properties
    acstable = property(lambda self:self.data['acstable'])
    title = property(lambda self:self.data['title'])
    subject = property(lambda self:self.data['subject'])
    lineno = property(lambda self:self.data['lineno'])
    seqstart = property(lambda self:self.data['seqstart'])
    seqno = property(lambda self:self.data['seqno'])
    
    def __init__(self, fileid=None, acstable=None, seqno=None, lineno=None, seqstart=None, cells=None, cellseq=None, title=None, subject=None):
        """Arguments from ACS table definition file:
            File ID, # Not used
            Table ID,
            Sequence Number,
            Line Number,
            Start Position,
            Total Cells in Table,
            Total Cells in Sequence,
            Table Title,
            Subject Area
        """
        self.data = dict(
            acstable = acstable,
            seqno = self._int(seqno),
            lineno = self._int(lineno),
            seqstart = self._int(seqstart),
            cells = cells,
            cellseq = self._int(cellseq),
            title = str(title).title(),
            subject = subject            
        )
        self.children = {}
    
    @classmethod
    def load(cls, filename):
        """Class method to load ACS table definition."""
        if cls.loaded:
            return
        print "Loading ACS table definitions: %s"%filename
        with open(filename) as f:
            reader = csv.reader(f)
            header = reader.next()
            for row in reader:
                row = [i.strip() for i in row]
                t = ACSMeta(
                    acstable = row[1],
                    seqno    = row[2],
                    lineno   = row[3],
                    seqstart = row[4],
                    cells    = row[5],
                    cellseq  = row[6],
                    title    = row[7],
                    subject  = row[8]
                )
                if t.seqstart is not None:
                    cls.acstables[t.acstable] = t
                else:
                    cls.acstables[t.acstable].addchild(t)        
        cls.loaded = True

    @classmethod
    def get(cls, acstable):
        """Get an ACS table definition by name, e.g. "B25034". """
        if acstable in cls.acstables:
            return cls.acstables[acstable]
        raise KeyError("Unknown ACS table: %s"%acstable)

    def addchild(self, child):
        """Add a child ACSMeta. For instance, "B25034" has 10 children
        corresponding to the 10 data columns."""
        if child.lineno is not None:
            child.data['acstable'] = '%s_%03d'%(child.acstable, child.lineno)
            self.children[child.lineno] = child

    def getchildren(self):
        return [v for k,v in sorted(self.children.items())]
        
    def printchildren(self):
        """Print a description of this table and its children."""
        print self.title
        for k,v in sorted(self.children.items()):
            print "\t", v.title

    def parse(self, row, geom=None):
        """Parse a row of an ACS summary data file. Return ACSTract."""
        data = {}
        for k,v in sorted(self.children.items()):
            # Have to do this b/c titles are not unique.
            # key = '%s / %s (%s)'%(self.title, v.title, k)
            value = row[self.seqstart+k-2] # -2 because indexed at 1.
            data[v.acstable] = self._int(value)

        logrecno = row[5]
        geoid = None
        if geom:
            geoid = geom.getgeoid(logrecno)
        return ACSTract(logrecno=logrecno, geoid=geoid, data=data)
        
    def _int(self, v):
        # convert a string to an int, or None
        try:
            return int(v.strip())
        except Exception, e:
            return None

class ACSGeometry(object):
    """Parse ACS Geometry file. This maps tract logrecno IDs to Census IDs."""
    
    def __init__(self, year, span, state):
        """Year, survey span, and state."""
        self.year = year
        self.span = span
        self.state = state
        self.geoids = {}
        
    def load(self):
        """Load the geometry file."""
        geofile = 'g%04d%01d%s.csv'%(self.year, self.span, self.state)
        print "Loading ACS Geometry: %s"%geofile
        with open(geofile) as f:
            reader = csv.reader(f)
            for row in reader:
                logrecno = row[4]
                geoid = row[48]
                self.geoids[logrecno] = geoid
    
    def getgeoid(self, logrecno):
        """Return a Census tract ID from a ACS logrecno."""
        geoid = self.geoids.get(logrecno)
        if geoid:
            return geoid.partition('US')[2]
        return None
                
class ACSShape(object):
    """Parse TIGER Shapefiles provided by ACS."""
    
    def __init__(self, shapedir):
        self.shapedir = shapedir
        self.shapes = {}
    
    def load(self):
        """Load the records and shapes from ACS Shapefiles."""
        import shapefile
        print "Loading Census Shapes: %s"%self.shapedir
        sf = shapefile.Reader(self.shapedir)
        for rec, shape in zip(sf.records(), sf.shapes()):
            geoid = rec[3]
            self.shapes[geoid] = (rec, shape)

    def getshape(self, geoid):
        """Return record and shape geometry by a Census ID."""
        if self.shapes.get(geoid):
            return self.shapes.get(geoid)
        return None, None
        
##### Load the ACS Table metadata #####

TABLES = ACSMeta()
def _load_acsmeta(acsmetapath=None):
    share = os.path.dirname(inspect.getfile(inspect.currentframe()))
    default = "Sequence_Number_and_Table_Number_Lookup.txt"
    TABLES.load(acsmetapath or os.path.join(share, 'docs', default))
_load_acsmeta()    



