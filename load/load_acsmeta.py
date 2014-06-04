"""Load ACS table definitions."""
import argparse
import cityism.acs
import cityism.config

def fix_word_quotes(value):
    return value.decode('windows-1252').encode('ascii', 'ignore')

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    query_acsmeta_create = """
        CREATE TABLE IF NOT EXISTS acsmeta (
            acstable VARCHAR NOT NULL PRIMARY KEY,
            title VARCHAR,
            subject VARCHAR
        );
    """
    
    query_acsmeta_insert = """
        INSERT INTO acsmeta 
        VALUES (%(acstable)s, %(title)s, %(subject)s)
        ;
    """

    with cityism.config.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query_acsmeta_create)
            for key, table in cityism.acs.ACSMeta.ACSTABLES.items():
                print "%s..."%table.acstable
                params = {}
                params.update(table.data)
                params['title'] = fix_word_quotes(params['title'])
                cursor.execute(query_acsmeta_insert, params)
                for k,child in table.children.items():
                    print "\t%s"%child.acstable
                    params = {}
                    params.update(child.data)
                    params['title'] = fix_word_quotes(params['title'])
                    cursor.execute(query_acsmeta_insert, params)
    

if __name__ == "__main__":
    main()
