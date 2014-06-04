"""Base query."""

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
    