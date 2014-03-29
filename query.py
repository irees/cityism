import argparse
import collections
import csv
import json
import os
import sys
import inspect
import shapefile
import acs
import math

import psycopg2
import psycopg2.extras

import config

CITIES = {
    'Houston': (29.7573869124592, -95.3631898316691),
    'Dallas': (32.779411, -96.806802),
    'Austin': (30.268035, -97.745333),
    'San Antonio': (29.424761, -98.493591),
    'Lubbock': (33.585527, -101.845632),
    'Galveston': (29.299392, -94.794328)
}

class Query(object):
    def __init__(self, conn=None):
        self.conn = conn

    def query(self):
        pass

class QueryACSTitle(Query):
    def query(self, acstable=None):
        query = """
            SELECT acstable, title, subject FROM acsmeta where acstable = %(acstable)s;
        """
        with self.conn.cursor() as cursor:
            params = {'acstable':acstable}
            cursor.execute(query, params)
            row = cursor.fetchone()
        return row[2]
    