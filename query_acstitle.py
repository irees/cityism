import math
import argparse

import cityism.acs
import cityism.config
import cityism.query

class QueryACSTitle(cityism.query.Query):
    def query(self, acstable=None):
        query = """
            SELECT acstable, title, subject FROM acsmeta where acstable = %(acstable)s;
        """
        with self.conn.cursor() as cursor:
            params = {'acstable':acstable}
            cursor.execute(query, params)
            row = cursor.fetchone()
        return row[2]
    
