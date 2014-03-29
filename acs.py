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

# TRACTS
# shp2pgsql -p -I -s 4269 tl_2012_01_tract.shp tracts | psql -d acs
# for i in *.shp;do shp2pgsql -s 4269 -a $i tracts | psql -d acs;done

# BLOCKS
# shp2pgsql -p -I -s 4269 tl_2012_01_tabblock.shp blocks | psql -d acs
# for i in tl_2012_*tabblock.shp;do shp2pgsql -s 4269 -a $i blocks | psql -d acs;done

# COUNTIES
# shp2pgsql -p -I -s 4269 tl_2012_us_county.shp counties | psql -d acs
# shp2pgsql -W LATIN1 -s 4269 -a tl_2012_us_county.shp counties | psql -d acs

# STATES
# shp2pgsql -p -I -s 4269 tl_2012_us_state.shp states | psql -d acs
# shp2pgsql -s 4269 -a tl_2012_us_state.shp states | psql -d acs

INTERESTING = ['B08303', 'B01001', 'B01002', 'B01003', 'B02001',
'B03002', 'B05001', 'B07002', 'B07009', 'B07010', 'B08006', 'B08012', 'B08119',
'B08121', 'B08124', 'B08126', 'B08134', 'B08141', 'B08301', 'B08519', 'B08521',
'B08526', 'B08601', 'B09001', 'B09002', 'B13002', 'B15001', 'B15002', 'B15003',
'B17001', 'B19001', 'B19061', 'B19083', 'B19101', 'B19301', 'B24011', 'B24121',
'B25001', 'B25002', 'B25003', 'B25004', 'B25009', 'B25010', 'B25012', 'B25014',
'B25024', 'B25026', 'B25034', 'B25038', 'B25045', 'B25046', 'B25056', 'B25061',
'B25063', 'B25064', 'B25070', 'B25075', 'B25081', 'B25087', 'B25113', 'B25115',
'C24010']

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
    ACSTABLES = {}
    LOADED = False

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

        if lineno:
            acstable = '%s_%03d'%(acstable, float(lineno))
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
        if cls.LOADED:
            return
        print "Loading ACS table definitions: %s"%filename
        with open(filename) as f:
            reader = csv.reader(f)
            header = reader.next()
            for row in reader:
                row = [i.strip() for i in row]
                basetable = row[1]
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
                if t.seqstart is None:
                    cls.ACSTABLES[basetable.lower()].addchild(t)        
                else:
                    cls.ACSTABLES[t.acstable.lower()] = t
        cls.LOADED = True

    @classmethod
    def get(cls, acstable):
        """Get an ACS table definition by name, e.g. "B25034". """
        acstable = acstable.lower()
        if acstable in cls.ACSTABLES:
            return cls.ACSTABLES[acstable]
        raise KeyError("Unknown ACS table: %s"%acstable)

    def addchild(self, child):
        """Add a child ACSMeta. For instance, "B25034" has 10 children
        corresponding to the 10 data columns."""
        if child.lineno is not None:
            self.children[child.lineno] = child

    def getchildren(self):
        """Get children (columns) in this table."""
        return [v for k,v in sorted(self.children.items())]
        
    def printchildren(self):
        """Print a description of this table and its children."""
        print self.title
        for k,v in sorted(self.children.items()):
            print "\t", v.title

    ##### Read files #####

    def read(self, year=2012, span=5, state='ca'):
        """Load data from the specified ACS survey summary files. Return ACSTracts."""
        # Load the data files.
        ret = []

        # Load logrecno / tract ID map.
        geom = ACSGeometry(year, span, state)
        geom.load()
        
        # Load ACS data.        
        filename = 'e%04d%01d%s%04d%03d.txt'%(year, span, state, self.seqno, 0)
        print "Loading ACS data: %s"%filename
        with open(filename) as f:
            reader = csv.reader(f)
            for row in reader:                
                tract = self.parse(row, geom=geom)
                ret.append(tract)
        return ret

    def parse(self, row, geom=None):
        """Parse a row of an ACS summary data file. Return ACSTract."""
        data = {}
        for k,v in sorted(self.children.items()):
            # Have to do this b/c titles are not unique.
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
        
class ACSFips(object):
    """FIPS codes for counties and states.
    
    H1: identifies an active county or statistically equivalent entity that
    does not qualify under subclass C7 or H6.

    H4: identifies a legally defined inactive or nonfunctioning county or
    statistically equivalent entity that does not qualify under subclass H6.

    H5: identifies census areas in Alaska, a statistical county equivalent
    entity.

    H6: identifies a county or statistically equivalent entity that is areally
    coextensive or governmentally consolidated with an incorporated place, part
    of an incorporated place, or a consolidated city.

    C7: identifies an incorporated place that is an independent city; that is, it
    also serves as a county equivalent because it is not part of any county, and a
    minor civil division (MCD) equivalent because it is not part of any MCD.
    """
    ANSI_STATES = {}
    ANSI_STATES_COUNTIES = {}
    STATES_ANSI = {}

    @classmethod
    def load(cls, filename):
        """Load the FIPS file."""
        print "Loading ACS FIPS mapping: %s"%filename
        with open(filename) as f:
            reader = csv.reader(f)
            header = reader.next()
            for row in reader:
                state, statefp, countyfp, county, c = row
                cls.ANSI_STATES[statefp] = state
                cls.ANSI_STATES_COUNTIES[(statefp, countyfp)] = county
                cls.STATES_ANSI[state] = statefp
        
##### Load the ACS Table metadata #####

def _load_acsmeta(acsmetapath=None):
    share = os.path.dirname(inspect.getfile(inspect.currentframe()))
    default = "Sequence_Number_and_Table_Number_Lookup.txt"
    ACSMeta.load(acsmetapath or os.path.join(share, 'data', default))
    
def _load_acsfips(acsfipspath=None):
    share = os.path.dirname(inspect.getfile(inspect.currentframe()))
    default = "national_county_fips.csv"
    ACSFips.load(acsfipspath or os.path.join(share, 'data', default))
        

_load_acsmeta()    
_load_acsfips()


