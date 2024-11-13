import sqlite3


class WikiCache:
    """
    Caches requests to check against Wikipedia.
    """
    def __init__(self, db_name='wiki-cache.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.create_entities_table()

    def create_entities_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS wiki_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity TEXT,
                    entity_exists INTEGER,
                    url TEXT
                )
            ''')

    def read_entity_rows(self, entity):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wiki_entities WHERE entity = ?', (entity,))
        rows = cursor.fetchall()
        return [
            {
                'id': row[0],
                'entity': row[1],
                'entity_exists': row[2] == 1,
                'url': row[3]
            }
            for row in rows
        ]

    def add_queries_row(self, entity, entity_exists, url):
        with self.conn:
            self.conn.execute('''
                INSERT INTO wiki_entities (entity, entity_exists, url)
                VALUES (?, ?, ?)
            ''', (entity, entity_exists, url))

    def close(self):
        self.conn.close()