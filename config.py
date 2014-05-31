"""Cityism configuration."""
import psycopg2
import psycopg2.extras

# TODO: Load from config.json
srid = 4326

host = 'localhost'
user = 'irees'
password = ''
port = 5432
dbname = 'acs'

def connect(**kwargs):
    kw = {'dbname': dbname, 'user': user, 'password': password, 'host':host, 'port': port}
    kw.update(kwargs)
    return psycopg2.connect(**kw)

