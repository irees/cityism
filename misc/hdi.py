"""Human Development Index.

Methods and data:
    http://en.wikipedia.org/wiki/Human_Development_Index
    http://ghdx.healthmetricsandevaluation.org/record/united-states-adult-life-expectancy-state-and-county-1987-2009
    http://glossary.uis.unesco.org/glossary/en/term/2179/en
    http://hdr.undp.org/en/statistics/hdi
    http://stats.uis.unesco.org/unesco/TableViewer/document.aspx?ReportId=121&IF_Language=eng&BR_Country=8400&BR_Region=40500
    http://www.nber.org/papers/w15902.pdf        
    http://www.uis.unesco.org/Education/Documents/gender-atlas-6-en.pdf
    http://www.uis.unesco.org/Education/Documents/mean-years-schooling-indicator-methodology-en.pdf
                
This map was inspired by a county-by-county HDI map:
    http://www.policymic.com/articles/85537/if-the-u-s-were-graded-using-the-un-s-index-for-african-development-here-s-what-we-d-see
    http://ispol.com/sasha/hdi/

For the calculations and notes, see:
    HDIRegion:
        row_mys
        row_eys
        row_le
        row_income
        calc_hdi        
"""
import math
import argparse
import json

import numpy

import psycopg2
import psycopg2.extras

import cityism.acs
import cityism.config
import cityism.query
from cityism.utils import *

def checkmax(v, maxvalue=1.0):
    if v > maxvalue:
        v = maxvalue
    return v    

class HDIRegion(object):
    """Calculate HDI for a region."""
    # I have included a reference of the ACS columns and values
    # at the bottom of this file.
    
    # Map of age ranges to grade levels to calculate enrollment,
    #   and Expected Years of Education.
    # label, years assigned, auto, age keys, enrollment keys
    eys_groups = [
        ['prek+k0', 1, True, acsrange('b01001', cols=(3, 27)), acsrange('b14001', 3, 4)],
        ['k1-4',    4, True, acsrange('b01001', cols=(4, 28)), acsrange('b14001', 5)],
        ['k5-8',    4, True, acsrange('b01001', cols=(5, 29)), acsrange('b14001', 6)],
        ['k9-12',   4, False, acsrange('b01001', cols=(6, 30)) + acsrange('b01001', cols=(7, 31), weight=0.5), acsrange('b14001', 7)],
        ['college', 4, False, acsrange('b01001', cols=(7, 31), weight=0.5) + acsrange('b01001', 8, 10)  + acsrange('b01001', 32, 34), acsrange('b14001', 8)],
        ['grad',    5, False, acsrange('b01001', 11) + acsrange('b01001', 35), acsrange('b14001', 9)]
    ]
    
    # Columns for Mean Years of Schooling
    # label, years assigned, keys
    mys_groups = [
        # K-12 years
        ['prek',  0,  acsrange('b15003', 3)],
        ['k0',    1,  acsrange('b15003', 4)],
        ['k1',    2,  acsrange('b15003', 5)],
        ['k2',    3,  acsrange('b15003', 6)],
        ['k3',    4,  acsrange('b15003', 7)],
        ['k4',    5,  acsrange('b15003', 8)],
        ['k5',    6,  acsrange('b15003', 9)],
        ['k6',    7,  acsrange('b15003', 10)],
        ['k7',    8,  acsrange('b15003', 11)],
        ['k8',    9,  acsrange('b15003', 12)],
        ['k9',    10, acsrange('b15003', 13)],
        ['k10',   11, acsrange('b15003', 14)],
        ['k11',   12, acsrange('b15003', 15)],
        ['k12no', 13, acsrange('b15003', 16)],
        ['k12',   13, acsrange('b15003', 17)],
        ['ged',   13, acsrange('b15003', 18)],
        ['sc1',   13, acsrange('b15003', 19)],                
        # Assign 2 years for >1yr college, AA
        ['aa',    15, acsrange('b15003', 20)],
        ['sc2',   15, acsrange('b15003', 21)],
        # Assign 4 years for Bachelor's
        ['ba',    17, acsrange('b15003', 22)],
        # Assign 2 years for Master's
        ['ms',    19, acsrange('b15003', 23)],
        # Assign 4 years for professional degree
        ['prof',    21, acsrange('b15003', 24)],
        # Assign 5 years for doctorate
        ['phd',   22, acsrange('b15003', 25)]
    ]    

    def __init__(self, **kwargs):
        """Set display attributes: geoid, geom, countyfp, statefp"""
        # Display
        self.geoid = kwargs.get('geoid')
        self.geom = kwargs.get('geom')
        self.countyfp = kwargs.get('countyfp')
        self.statefp = kwargs.get('statefp')
        self.name = kwargs.get('name') # census tract name
        self.aland = kwargs.get('aland')
        self.awater = kwargs.get('awater')
        self.label = self._getlabel()
        self.pop = 0
        # Raw values
        self.eys = None
        self.mys = None
        self.le = None
        self.income = None
        # HDI components
        self.ei = None
        self.lei = None
        self.ii = None
        self.hdi = None
    
    def _getlabel(self):
        """Display label."""
        c = cityism.acs.ACSFips.ANSI_STATES_COUNTIES.get((self.statefp, self.countyfp))
        s = cityism.acs.ACSFips.ANSI_STATES.get(self.statefp)
        return "%s, %s tract %s"%(c, s, self.name)
    
    def data_rounded(self, r=3):
        """Round data for display."""
        def _round(i, r):
            if isinstance(i, float):
                return round(i, r)
            return i
        d = {}
        for k,v in self.__dict__.items():
            d[k] = _round(v, r)
        return d
    
    ##### Calculate HDI Components #####
    
    def row_eys(self, row):
        """Calculate Expected Years of Schooling (EYS).
        
        References:
        http://glossary.uis.unesco.org/glossary/en/term/2179/en
        http://www.uis.unesco.org/Education/Documents/gender-atlas-6-en.pdf
        http://stats.uis.unesco.org/unesco/TableViewer/document.aspx?ReportId=121&IF_Language=eng&BR_Country=8400&BR_Region=40500

        EYS is the number of years a person can expect to complete. It is
        calculated based on enrollment ratios at each grade level and the
        duration of each grade level.
        
        After spending time with the data, this is the least spatially cohesive
        of the HDI components with the tract level census data. So, I have
        limited it to just enrollment ratios of 9th-12th grade, college, and
        grad school. This should at least provide a measure of the number of
        kids graduating from primary school and entering college. The UN
        caps EYS at 18 years. A few college towns (Berkeley) hit the cap.
        """
        r = []
        for label, years, auto, age_keys, enr_keys in self.eys_groups:
            # Calculate expected enrollment based on pop by age
            pop_expect = float(sum([row[key.acstable]*key.weight for key in age_keys]))
            # Calculate actual enrollment in the corresponding grades
            pop_enroll = float(sum([row[key.acstable]*key.weight for key in enr_keys]))
            # If pop is zero.
            try:
                ratio = pop_enroll / pop_expect
            except ZeroDivisionError:
                ratio = 0.0
            # If enrollment is higher than expected..
            if ratio > 1:
                ratio = 1.0
            # Data is unreliable below grade 9 :(
            if auto:
                ratio = 1.0
            # Expected years of education is sum of 
            # the enrollment by grade bracket * years in grade bracket.
            r.append(ratio*years)
            print "EYS:", label, "enroll:", pop_enroll, "expect:", pop_expect, "ratio: %0.2f"%ratio, "ratio*years: %0.2f"%(ratio * years)
        # Sum.
        self.eys = sum(r)
        print "EYS final:", self.eys
    
    def row_mys(self, row):
        """Calculate Mean Years of Schooling (MYS).

        References:
        http://www.uis.unesco.org/Education/Documents/mean-years-schooling-indicator-methodology-en.pdf
        http://www.nber.org/papers/w15902.pdf        
        
        This is similar to the UIS UNESCO method outlined above. For each level
        of educational attainment, the number of years to reach that level is
        multipled by the percentage of population over 25 years old that
        reached that level. The MYS is the sum of all levels. I ignored pre-K,
        and started with kindergarten as the first year. High school would then
        be 13 years (1+12), associates degree is 15 (1+12+2), undergraduate
        degree is 17 (1+12+4). Professional school is 21 (...+4). PhD obviously
        varies, but I assigned 22 years (...+5).
        """
        r = []
        pop_25_keys = acsrange('b01001', 11, 25) + acsrange('b01001', 35, 49)
        pop_25 = sum(row[key.acstable]*key.weight for key in pop_25_keys)
        for label, years, keys in self.mys_groups:
            for key in keys:
                try:
                    p = row[key.acstable] / pop_25
                except ZeroDivisionError:
                    p = 0.0
                i = years * p
                r.append(i)
                print "MYS:", label, "years:", years, "key:", key.acstable, "value:", row[key.acstable], "pct:", p, "value:", i                
        self.mys = sum(r)
        print "MYS final:", self.mys
        
    def row_income(self, row):
        """Calculate per-capita income values for past 12 months... This one is easy!"""
        self.income = row.get('b19301_001')
        print "income final:", self.income

    def row_le(self, row):
        """Calculate life expectancy... Also easy!"""
        self.le = row.get('le')
        print "le final:", self.le

    def row_pop(self, row):
        """Population."""
        self.pop = row.get('b01001_001')
        self.pop_d = self.pop / self.aland * 1e6
        self.pop_dmi = self.pop_d * 2.58999
        print "pop final:", self.pop, "... density:", self.pop_d, self.pop_dmi
        
    def calc_hdi(self, mys_min, mys_max, eys_min, eys_max, le_min, le_max, income_min, income_max, ei_min=0.0, ei_max=1.0):
        """Calculate HDI components from previously set income, le, mys, eys."""
        if not self.mys:
            raise ValueError("Incomplete data, missing: mys")
        elif not self.eys:
            raise ValueError("Incomplete data, missing: eys")
        elif not self.le:
            raise ValueError("Incomplete data, missing: le")
        elif not self.income:
            raise ValueError("Incomplete data, missing: income")
        req = [self.mys, self.eys, self.le, self.income]
        if 0 in req:
            raise ValueError("ZERO!")

        # HDI is composed of 3 indices:
        # ... Education Index is geometric mean of MYS / Max observed MYS, 
        #     and, EYS / Max observed EYS
        #     (Please read notes in self.row_mys and self.row_eys above)
        mys = (self.mys - mys_min) / (mys_max - mys_min)
        eys = (self.eys - eys_min) / (eys_max - eys_min)
        ei = (checkmax(mys) * checkmax(eys)) ** 0.5
        self.ei = checkmax(ei / ei_max)
        # ... Income Index is (ln(income) - ln(min income)) / (ln(max income) 
        #     - ln(income_min))
        #     (This is designed to show decreasing importance torwards max)
        ii = ( math.log(self.income) - math.log(income_min) ) / ( math.log(income_max) - math.log(income_min) )
        self.ii = checkmax(ii / ei_max)
        # ... LE is simple normalized LE. 
        lei = (self.le - le_min) / (le_max - le_min)
        self.lei = checkmax(lei)
        
        # ... Final HDI is geometric mean of 3 indices:
        self.hdi = (self.lei * self.ei * self.ii) ** (1/3.0)
        print "hdi ei:", self.ei
        print "hdi ii:", self.ii
        print "hdi lei:", self.lei
        print "hdi final:", self.hdi

class QueryHDI(cityism.query.Query):
    """This map applies the United Nations Development Programme Human
    Development Index (HDI) -- a composite measure of Life Expectancy,
    Education, and Income levels -- to United States census tracts."""

    # TileMill notes:
    # +proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs
    
    # ACS Tables used:
    #   B01001 SEX BY AGE
    #   B14001 SCHOOL ENROLLMENT BY LEVEL OF SCHOOL FOR THE POPULATION 3 YEARS AND OVER
    #   B15003 EDUCATIONAL ATTAINMENT FOR THE POPULATION 25 YEARS AND OVER
    #   B19301 PER CAPITA INCOME IN THE PAST 12 MONTHS (IN 2012 INFLATION-ADJUSTED DOLLARS)
    
    def query(self, statefp='06', countyfp='075', **kwargs):
        # Grab the ACS tables for education, income, life expectancy.
        # Keep aland, awater, labels, etc. handy for future use.
        query = """
            SELECT
                tiger.gid,
                tiger.geoid,
                tiger.countyfp,
                tiger.statefp,
                tiger.aland,
                tiger.awater,
                tiger.name,
                ST_AsText(tiger.geom) AS geom,
                data_life_expectancy.le AS le,
                acs_b01001.*,
                acs_b14001.*,
                acs_b15003.*,
                acs_b19301.*
            FROM
                tract_2012 AS tiger
            INNER JOIN
                acs_b01001 ON tiger.geoid = acs_b01001.geoid
            INNER JOIN
                acs_b14001 ON tiger.geoid = acs_b14001.geoid
            INNER JOIN
                acs_b15003 ON tiger.geoid = acs_b15003.geoid
            INNER JOIN
                acs_b19301 ON tiger.geoid = acs_b19301.geoid
            INNER JOIN
                data_life_expectancy ON tiger.statefp = data_life_expectancy.statefp AND tiger.countyfp = data_life_expectancy.countyfp
            WHERE
                tiger.aland > 0;
        """
        # WHERE
        #  tiger.statefp = %%(statefp)s AND
        #  tiger.countyfp = %%(countyfp)s AND

        regions = []
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, {'statefp':statefp, 'countyfp':countyfp})
            for row in cursor:
                print "=========="
                print row.get('geoid')
                region = HDIRegion(**row)
                region.row_pop(row)
                region.row_eys(row)
                region.row_mys(row)
                region.row_le(row)
                region.row_income(row)
                regions.append(region)

        # Gather the goalposts.
        mys = valueattr(regions, 'mys', minvalue=0)
        eys = valueattr(regions, 'eys', minvalue=0)
        income = valueattr(regions, 'income', minvalue=0)
        le = valueattr(regions, 'le', minvalue=0)

        mys_min    = kwargs.get('mys_min') or min(mys)
        mys_max    = kwargs.get('mys_max') or max(mys)
        eys_min    = kwargs.get('eys_min') or min(eys)
        eys_max    = kwargs.get('eys_max') or max(eys)
        le_min     = kwargs.get('le_min') or min(le)
        le_max     = kwargs.get('le_max') or max(le)
        income_min = kwargs.get('income_min') or min(income)
        income_max = kwargs.get('income_max') or max(income)

        # Update HDI components.
        for region in regions:
            try:
                region.calc_hdi(mys_min=mys_min, mys_max=mys_max, eys_min=eys_min, eys_max=eys_max, le_min=le_min, le_max=le_max, income_min=income_min, income_max=income_max)        
            except ValueError, e:
                print "Skipping:", e
        return regions
        
    def stats(self, regions):
        """Region statistics."""
        def statattr(items, key):
            values = valueattr(items, key, minvalue=0)
            print "Statistics for %s:"%key
            print "\t", "len: %s"%len(items)
            print "\t", "> 0: %s"%(len(values))
            print "\t", "min: %0.2f"%min(values)
            for p in (1, 5, 50, 95, 99):
                print "\t", "%s: %0.2f"%(p, numpy.percentile(values, p))
            print "\t", "max: %0.2f"%max(values)
            for p in range(10, 110, 10):
                print "\t", "dec %s: %0.2f"%(p, numpy.percentile(values, p))

        print "Raw components:"
        for key in ['mys', 'eys', 'income', 'le', 'pop']:
            statattr(regions, key)
        print "HDI Components:"
        for key in ['hdi', 'ei', 'ii', 'lei']:
            statattr(regions, key)

    def save_query(self, regions, table):
        """Save regions to table."""
 
       # Copy the geometry as well to simplify rendering / export.
        query_create = """
            DROP TABLE IF EXISTS %(table)s;
            CREATE TABLE result_hdi (
                gid serial NOT NULL PRIMARY KEY,
                geoid varchar,
                aland float,
                awater float,
                statefp varchar,
                countyfp varchar,
                name varchar,
                label varchar,
                hdi float,
                lei float,
                ei float,
                ii float,
                mys float,
                eys float,
                income float,
                le float,
                pop float,
                pop_d float,
                pop_dmi float
            );
            SELECT 
                AddGeometryColumn('result_hdi', 'geom', 4326, 'MultiPolygon', 2);
        """%{'table':table}
        
        query_insert = """
            INSERT INTO %(table)s(
                geoid,
                aland,
                awater,
                statefp,
                countyfp,
                name,
                label,
                hdi, 
                ei, 
                ii, 
                lei, 
                mys,
                eys, 
                income, 
                le,
                pop,
                pop_d,
                pop_dmi,
                geom
            ) 
            VALUES (
                %%(geoid)s, 
                %%(aland)s,
                %%(awater)s,
                %%(statefp)s,
                %%(countyfp)s,
                %%(name)s,
                %%(label)s,
                %%(hdi)s,
                %%(ei)s, 
                %%(ii)s, 
                %%(lei)s, 
                %%(mys)s, 
                %%(eys)s, 
                %%(income)s, 
                %%(le)s,
                %%(pop)s,
                %%(pop_d)s,
                %%(pop_dmi)s,
                ST_GeomFromText(%%(geom)s, 4326)
            );
        """%{'table':table}
        
        with self.conn.cursor() as cursor:
            print "Saving to: %s"%table    
            cursor.execute(query_create)
            for region in regions:
                print "insert: ", region.geoid
                cursor.execute(query_insert, region.data_rounded())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiger", help="TIGERLine table", default="tract_2012")
    parser.add_argument("--save", help="Save result to table")
    args = parser.parse_args()
    
    with cityism.config.connect() as conn:
        q = QueryHDI(conn=conn)
        # Goalposts from 2013 HDI report:
        # http://hdr.undp.org/sites/default/files/hdr_2013_en_technotes.pdf
        result = q.query(level=args.level, le_min=20, le_max=83.6, mys_min=0.0, mys_max=13.3, eys_min=0.0, eys_max=18.0, income_min=100, income_max=87478, ei_max=0.971)
        if args.save:
            q.save_query(result, table=args.save)
        q.stats(result)

########### Reference for ACS tables used ###########

# ACSSF,B01001,0002, ,7,49 CELLS, ,SEX BY AGE,Age-Sex
# ACSSF,B01001,0002, , ,, ,Universe:  Total population,
# ACSSF,B01001,0002,1, ,, ,Total:,
# ACSSF,B01001,0002,2, ,, ,Male:,
# ACSSF,B01001,0002,3, ,, ,Under 5 years,
# ACSSF,B01001,0002,4, ,, ,5 to 9 years,
# ACSSF,B01001,0002,5, ,, ,10 to 14 years,
# ACSSF,B01001,0002,6, ,, ,15 to 17 years,
# ACSSF,B01001,0002,7, ,, ,18 and 19 years,
# ACSSF,B01001,0002,8, ,, ,20 years,
# ACSSF,B01001,0002,9, ,, ,21 years,
# ACSSF,B01001,0002,10, ,, ,22 to 24 years,
# ACSSF,B01001,0002,11, ,, ,25 to 29 years,
# ACSSF,B01001,0002,12, ,, ,30 to 34 years,
# ACSSF,B01001,0002,13, ,, ,35 to 39 years,
# ACSSF,B01001,0002,14, ,, ,40 to 44 years,
# ACSSF,B01001,0002,15, ,, ,45 to 49 years,
# ACSSF,B01001,0002,16, ,, ,50 to 54 years,
# ACSSF,B01001,0002,17, ,, ,55 to 59 years,
# ACSSF,B01001,0002,18, ,, ,60 and 61 years,
# ACSSF,B01001,0002,19, ,, ,62 to 64 years,
# ACSSF,B01001,0002,20, ,, ,65 and 66 years,
# ACSSF,B01001,0002,21, ,, ,67 to 69 years,
# ACSSF,B01001,0002,22, ,, ,70 to 74 years,
# ACSSF,B01001,0002,23, ,, ,75 to 79 years,
# ACSSF,B01001,0002,24, ,, ,80 to 84 years,
# ACSSF,B01001,0002,25, ,, ,85 years and over,
# ACSSF,B01001,0002,26, ,, ,Female:,
# ACSSF,B01001,0002,27, ,, ,Under 5 years,
# ACSSF,B01001,0002,28, ,, ,5 to 9 years,
# ACSSF,B01001,0002,29, ,, ,10 to 14 years,
# ACSSF,B01001,0002,30, ,, ,15 to 17 years,
# ACSSF,B01001,0002,31, ,, ,18 and 19 years,
# ACSSF,B01001,0002,32, ,, ,20 years,
# ACSSF,B01001,0002,33, ,, ,21 years,
# ACSSF,B01001,0002,34, ,, ,22 to 24 years,
# ACSSF,B01001,0002,35, ,, ,25 to 29 years,
# ACSSF,B01001,0002,36, ,, ,30 to 34 years,
# ACSSF,B01001,0002,37, ,, ,35 to 39 years,
# ACSSF,B01001,0002,38, ,, ,40 to 44 years,
# ACSSF,B01001,0002,39, ,, ,45 to 49 years,
# ACSSF,B01001,0002,40, ,, ,50 to 54 years,
# ACSSF,B01001,0002,41, ,, ,55 to 59 years,
# ACSSF,B01001,0002,42, ,, ,60 and 61 years,
# ACSSF,B01001,0002,43, ,, ,62 to 64 years,
# ACSSF,B01001,0002,44, ,, ,65 and 66 years,
# ACSSF,B01001,0002,45, ,, ,67 to 69 years,
# ACSSF,B01001,0002,46, ,, ,70 to 74 years,
# ACSSF,B01001,0002,47, ,, ,75 to 79 years,
# ACSSF,B01001,0002,48, ,, ,80 to 84 years,
# ACSSF,B01001,0002,49, ,, ,85 years and over,

# ACSSF,B14001,0041, ,7,10 CELLS, ,SCHOOL ENROLLMENT BY LEVEL OF SCHOOL FOR THE POPULATION 3 YEARS AND OVER,School Enrollment
# ACSSF,B14001,0041, , ,, ,Universe:  Population 3 years and over,
# ACSSF,B14001,0041,1, ,, ,Total:,
# ACSSF,B14001,0041,2, ,, ,Enrolled in school:,
# ACSSF,B14001,0041,3, ,, ,"Enrolled in nursery school, preschool",
# ACSSF,B14001,0041,4, ,, ,Enrolled in kindergarten,
# ACSSF,B14001,0041,5, ,, ,Enrolled in grade 1 to grade 4,
# ACSSF,B14001,0041,6, ,, ,Enrolled in grade 5 to grade 8,
# ACSSF,B14001,0041,7, ,, ,Enrolled in grade 9 to grade 12,
# ACSSF,B14001,0041,8, ,, ,"Enrolled in college, undergraduate years",
# ACSSF,B14001,0041,9, ,, ,Graduate or professional school,
# ACSSF,B14001,0041,10, ,, ,Not enrolled in school,

# ACSSF,B15003,0043, ,125,25 CELLS, ,EDUCATIONAL ATTAINMENT FOR THE POPULATION 25 YEARS AND OVER,Educational Attainment
# ACSSF,B15003,0043, , ,, ,Universe:  Population 25 years and over,
# ACSSF,B15003,0043,1, ,, ,Total:,
# ACSSF,B15003,0043,2, ,, ,No schooling completed,
# ACSSF,B15003,0043,3, ,, ,Nursery school,
# ACSSF,B15003,0043,4, ,, ,Kindergarten,
# ACSSF,B15003,0043,5, ,, ,1st grade,
# ACSSF,B15003,0043,6, ,, ,2nd grade,
# ACSSF,B15003,0043,7, ,, ,3rd grade,
# ACSSF,B15003,0043,8, ,, ,4th grade,
# ACSSF,B15003,0043,9, ,, ,5th grade,
# ACSSF,B15003,0043,10, ,, ,6th grade,
# ACSSF,B15003,0043,11, ,, ,7th grade,
# ACSSF,B15003,0043,12, ,, ,8th grade,
# ACSSF,B15003,0043,13, ,, ,9th grade,
# ACSSF,B15003,0043,14, ,, ,10th grade,
# ACSSF,B15003,0043,15, ,, ,11th grade,
# ACSSF,B15003,0043,16, ,, ,"12th grade, no diploma",
# ACSSF,B15003,0043,17, ,, ,Regular high school diploma,
# ACSSF,B15003,0043,18, ,, ,GED or alternative credential,
# ACSSF,B15003,0043,19, ,, ,"Some college, less than 1 year",
# ACSSF,B15003,0043,20, ,, ,"Some college, 1 or more years, no degree",
# ACSSF,B15003,0043,21, ,, ,Associate's degree,
# ACSSF,B15003,0043,22, ,, ,Bachelor's degree,
# ACSSF,B15003,0043,23, ,, ,Master's degree,
# ACSSF,B15003,0043,24, ,, ,Professional school degree,
# ACSSF,B15003,0043,25, ,, ,Doctorate degree,

# ACSSF,B19301,0064, ,172,1 CELL, ,PER CAPITA INCOME IN THE PAST 12 MONTHS (IN 2012 INFLATION-ADJUSTED DOLLARS),Income
# ACSSF,B19301,0064, , ,, ,Universe:  Total population,
# ACSSF,B19301,0064,1, ,, ,Per capita income in the past 12 months (in 2012 inflation-adjusted dollars),

