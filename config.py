import psycopg2

srid = 4269

host = 'localhost'
user = 'postgres'
password = 'postgres'
port = 5432
dbname = 'acs'

def connect(**kwargs):
    kw = {'dbname': dbname, 'user': user, 'password': password, 'host':host, 'port': port}
    kw.update(kwargs)
    return psycopg2.connect(**kw)