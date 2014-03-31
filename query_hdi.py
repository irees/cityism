"""Human Development Index.

Methods and data:
  http://hdr.undp.org/en/statistics/hdi
  http://en.wikipedia.org/wiki/Human_Development_Index
  http://ghdx.healthmetricsandevaluation.org/record/united-states-adult-life-expectancy-state-and-county-1987-2009

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

# ACSSF,B14007,0041, ,206,19 CELLS, ,SCHOOL ENROLLMENT BY DETAILED  LEVEL OF SCHOOL FOR THE POPULATION 3 YEARS AND OVER,School Enrollment
# ACSSF,B14007,0041, , ,, ,Universe: Population 3 years and over,
# ACSSF,B14007,0041,1, ,, ,Total:,
# ACSSF,B14007,0041,2, ,, ,Enrolled in school:,
# ACSSF,B14007,0041,3, ,, ,"Enrolled in nursery school, preschool",
# ACSSF,B14007,0041,4, ,, ,Enrolled in kindergarten,
# ACSSF,B14007,0041,5, ,, ,Enrolled in grade 1,
# ACSSF,B14007,0041,6, ,, ,Enrolled in grade 2,
# ACSSF,B14007,0041,7, ,, ,Enrolled in grade 3,
# ACSSF,B14007,0041,8, ,, ,Enrolled in grade 4,
# ACSSF,B14007,0041,9, ,, ,Enrolled in grade 5,
# ACSSF,B14007,0041,10, ,, ,Enrolled in grade 6,
# ACSSF,B14007,0041,11, ,, ,Enrolled in grade 7,
# ACSSF,B14007,0041,12, ,, ,Enrolled in grade 8,
# ACSSF,B14007,0041,13, ,, ,Enrolled in grade 9,
# ACSSF,B14007,0041,14, ,, ,Enrolled in grade 10,
# ACSSF,B14007,0041,15, ,, ,Enrolled in grade 11,
# ACSSF,B14007,0041,16, ,, ,Enrolled in grade 12,
# ACSSF,B14007,0041,17, ,, ,"Enrolled in college, undergraduate years",
# ACSSF,B14007,0041,18, ,, ,Graduate or professional school,
# ACSSF,B14007,0041,19, ,, ,Not enrolled in school,

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

class HDIRegion(object):
    """Calculate HDI for a region."""
    # Map of age ranges to grade levels to calculate enrollment,
    #   and Expected Years of Education.
    # label, years assigned, auto, age keys, enrollment keys
    eys_groups = [
        # Age: Under 5
        ['pre-k',   1, True,  acsrange('b01001', cols=(3, 27)), acsrange('b14007', 3)],
        # Age: 5-9
        ['k-4',     5, True,  acsrange('b01001', cols=(4 ,28)), acsrange('b14007', 4, 8)],
        # Age: 9-14
        ['5-9',     5, True,  acsrange('b01001', cols=(5, 29)), acsrange('b14007', 9, 13)],
        # Age: 15-17
        ['10-12',   3, True,  acsrange('b01001', cols=(6, 30)),  acsrange('b14007', 14, 16)],
        # 17-25
        ['college', 4, False, acsrange('b01001', 7, 11)  + acsrange('b01001', 31, 35), acsrange('b14007', 17)],
        # 25-35
        ['grad',    4, False, acsrange('b01001', 11, 15) + acsrange('b01001', 35, 39), acsrange('b14007', 18)]
    ]    
    
    # Columns for Mean Years of Schooling
    # label, years assigned, keys
    mys_groups = [
        # K-12 years
        ['pre-k', 1,  'b15003_003'],
        ['k',     2,  'b15003_004'],
        ['k1',    3,  'b15003_005'],
        ['k2',    4,  'b15003_006'],
        ['k3',    5,  'b15003_007'],
        ['k4',    6,  'b15003_008'],
        ['k5',    7,  'b15003_009'],
        ['k6',    8,  'b15003_010'],
        ['k7',    9,  'b15003_011'],
        ['k8',    10, 'b15003_012'],
        ['k9',    11, 'b15003_013'],
        ['k10',   12, 'b15003_014'],
        ['k11',   13, 'b15003_015'],
        ['k12no', 14, 'b15003_016'],
        ['k12',   14, 'b15003_017'],
        ['ged',   14, 'b15003_018'],
        ['sc1',   14, 'b15003_019'],                
        # Assign 2 years for >1yr college, AA
        ['aa',    16, 'b15003_020'],
        ['sc2',   16, 'b15003_021'],
        # Assign 4 years for Bachelor's
        ['ba',    18, 'b15003_022'],
        # Assign 2 years for Master's
        ['ms',    20, 'b15003_023'],
        # Assign 4 years for MD / PhD
        ['md',    24, 'b15003_024'],
        ['phd',   24, 'b15003_025']
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
        # Indexes
        self.ei = None
        self.lei = None
        self.ii = None
        self.hdi = None
    
    def _getlabel(self):
        """Display label."""
        c = cityism.acs.ACSFips.ANSI_STATES_COUNTIES.get((self.statefp, self.countyfp))
        s = cityism.acs.ACSFips.ANSI_STATES.get(self.statefp)
        return "%s, %s #%s"%(c, s, self.name)
    
    def data(self):
        """Return dict, e.g. for insert."""
        return self.__dict__
    
    ##### Calculate HDI Components #####
    
    def row_eys(self, row):
        """Calculate Expected Years of Schooling (EYS).
        
        Note that we are estimating expected years of schooling
        from enrollment by grade level at a single point in time.
        This may be influenced by local factors such as where 
        colleges are located, tracts with very few children, etc.
        It would be better to follow a single cohort of students
        and measure their enrollment rates over time.
        """
        r = []
        for label, years, auto, age, enr in self.eys_groups:
            # Calculate expected enrollment based on pop by age
            pop_expect = float(sum([row[k] for k in age]))
            # Calculate actual enrollment in the corresponding grades
            pop_enroll = float(sum([row[k] for k in enr]))
            # If pop is zero.
            try:
                ratio = pop_enroll / pop_expect
            except ZeroDivisionError:
                ratio = 0.0
            # If enrollment is higher than expected..
            if ratio > 1:
                ratio = 1.0
            # Some tracts have fuzzy numbers... Just award years for lower grades.
            if ratio < 0.2 and auto:
                ratio = 1.0
            # Expected years of education is sum of 
            # the enrollment by grade bracket * years in grade bracket.
            r.append(ratio*years)
            print "EYS:", label, ratio, "enroll:", pop_enroll, "expect:", pop_expect, "ratio*years", ratio * years
        # Do the sum and round.
        self.eys = round(sum(r), 3)
        print "EYS final:", self.eys
    
    def row_mys(self, row):
        """Calculate Mean Years of Schooling (MYS).
        
        This calculation takes each level of educational attainment,
        and divides by the population of adults over 25 years old.
        Years are assigned based on how many years of schooling to reach
        each point. Pre-K is a given year, although I realize it's not
        universal. So, a high-school graduate is awarded 14 years (prek+k+12),
        associates degree is 16, ba/bs is 18 years, etc. I use 4 years
        for grad school (hahaha), although I should look up actual mix.
        """
        r = []
        pop_25_keys = acsrange('b01001', 11, 25) + acsrange('b01001', 35, 49)
        pop_25 = sum(row[k] for k in pop_25_keys)
        for label, years, key in self.mys_groups:
            print "MYS:", label, years, key, row[key], "years*value:", years*row[key]
            r.append(years*row[key])
        print "MYS total:", sum(r)
        try:
            m = sum(r) / float(pop_25)
        except ZeroDivisionError:
            m = 0
        self.mys = round(m, 3)  
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
        print "pop final:", self.pop
        
    def calc_hdi(self, mys_max, eys_max, le_min, le_max, income_min, income_max):
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
        # ... Education Index is geometricmean of MYS / Max observed MYS, and, EYS / Max observed EYS
        #     (Please read notes in self.row_mys and self.row_eys above)
        self.ei = ( (self.mys / mys_max) * (self.eys / eys_max) ) ** 0.5
        # ... Income Index is (ln(income) - ln(min income)) / (ln(max income) - ln(income_min))
        #     (This is designed to show decreasing importance as you approach max income)
        self.ii = ( math.log(self.income) - math.log(income_min) ) / (math.log(income_max) - math.log(income_min) )
        # ... LE is simple normalized LE. 
        #     (Since even the lowest US county is ~65 years, 
        #      you might set min to 50 to decrease importance of this factor)
        self.lei = (self.le - le_min) / (le_max - le_min)
        # ... Final HDI is geometric mean of 3 indices:
        self.hdi = (self.lei * self.ei * self.ii) ** 0.3333
        
        # Round to 3 digits...
        self.hdi = round(self.hdi, 3)
        print "hdi ei:", self.ei
        print "hdi ii:", self.ii
        print "hdi lei:", self.lei
        print "hdi final:", self.hdi

class QueryHDI(cityism.query.Query):
    """This map applies the United Nations Development Programme Human
    Development Index (HDI) -- a composite measure of Life Expectancy,
    Education, and Income levels -- to United States census tracts. While the
    UN HDI spans across the globe, this "disaggregated" HDI is normalized
    across 74,133 tracts to show relative differences within a single
    country."""

    # TileMill notes:
    # +proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs.
    
    # ACS Tables used:
    #   B01001 SEX BY AGE
    #   B14007 SCHOOL ENROLLMENT BY DETAILED    LEVEL OF SCHOOL FOR THE POPULATION 3 YEARS AND OVER
    #   B15003 EDUCATIONAL ATTAINMENT FOR THE POPULATION 25 YEARS AND OVER
    #   B19301 PER CAPITA INCOME IN THE PAST 12 MONTHS (IN 2012 INFLATION-ADJUSTED DOLLARS)
    
    def query(self, level='tracts', statefp='06', countyfp='075'):
        # Grab the ACS tables for education, income, life expectancy.
        # Keep aland, awater, labels, etc. handy for future use.
        assert level in ['tracts', 'blocks', 'counties', 'states']
        query = """
            SELECT
                %(level)s.gid,
                %(level)s.geoid,
                %(level)s.countyfp,
                %(level)s.statefp,
                %(level)s.aland,
                %(level)s.awater,
                %(level)s.name,
                ST_AsText(%(level)s.geom) AS geom,
                data_life_expectancy.value AS le,
                acs_b01001.*,
                acs_b14007.*,
                acs_b15003.*,
                acs_b19301.*
            FROM
                %(level)s
            INNER JOIN
                acs_b01001 ON %(level)s.geoid = acs_b01001.geoid
            INNER JOIN
                acs_b14007 ON %(level)s.geoid = acs_b14007.geoid
            INNER JOIN
                acs_b15003 ON %(level)s.geoid = acs_b15003.geoid
            INNER JOIN
                acs_b19301 ON %(level)s.geoid = acs_b19301.geoid
            INNER JOIN
                data_life_expectancy ON %(level)s.statefp = data_life_expectancy.statefp AND %(level)s.countyfp = data_life_expectancy.countyfp
            WHERE
                tracts.aland > 0;
        """%{'level':level}
        # WHERE
        #     tracts.statefp = %%(statefp)s
        #     tracts.countyfp = %%(countyfp)s

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

        # Update HDI components.
        # Note: I decided to set LE min to 50 instead of ~65 from the data.
        k = {'mys_max':max(mys), 'eys_max':max(eys), 'le_min':50.0, 'le_max':max(le), 'income_min':min(income), 'income_max':max(income)}
        for region in regions:
            try:
                region.calc_hdi(**k)        
            except ValueError, e:
                print "Skipping:", e
        return regions
        
    def stats(self, regions):
        """Region statistics."""
        for region in sorted(regions, key=lambda x:x.hdi):
            print "==========", region.geoid
            for k,v in sorted(region.data().items()):
                if k != 'geom':
                    print k, v

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
                pop float        
            );
            SELECT 
                AddGeometryColumn('result_hdi', 'geom', 4269, 'MultiPolygon', 2);
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
                ST_GeomFromText(%%(geom)s, 4269)
            );
        """%{'table':table}
        
        with self.conn.cursor() as cursor:
            print "Saving to: %s"%table    
            cursor.execute(query_create)
            for region in regions:
                print "insert: ", region.geoid
                cursor.execute(query_insert, region.data())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", help="Census geography level", default="tracts")
    parser.add_argument("--save", help="Save result to table")
    args = parser.parse_args()
    with cityism.config.connect() as conn:
        q = QueryHDI(conn=conn)
        result = q.query(level=args.level)
        if args.save:
            q.save_query(result, table=args.save)
        q.stats(result)

