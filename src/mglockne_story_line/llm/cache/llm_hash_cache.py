import sqlite3
from os import makedirs
from os.path import exists, join
from typing import Dict


class LLMHashCache:
    """
    Stores LLM responses and makes them accessible via the hash (and LLM version) of the prompt.
    Uses a sqlite DB as a backend.
    """
    def __init__(self, db_name: str = "query_cache.db", dir_name: str = './cache'):
        """
        :param db_name      Name of the resulting file
        :param dir_name     Name of the directory
        """
        if not exists(dir_name):
            makedirs(dir_name)
        self.conn = sqlite3.connect(join(dir_name, db_name))
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT,
                    llm TEXT,
                    result TEXT,
                    query TEXT,
                    PRIMARY KEY (query_hash, llm)
                )
            ''')

    def has_query(self, query: str) -> bool:
        cursor = self.conn.execute('''
            SELECT 1 FROM query_cache WHERE query = ?
        ''', (query,))
        return cursor.fetchone() is not None

    def length(self) -> int:
        cursor = self.conn.execute('''
            SELECT COUNT(*) FROM query_cache
        ''')

        count = cursor.fetchone()[0]
        return count

    def has_hash(self, query_hash: str, llm: str) -> bool:
        cursor = self.conn.execute('''
            SELECT 1 FROM query_cache WHERE query_hash = ? AND llm = ?
        ''', (query_hash, llm))
        result_exists: bool = cursor.fetchone() is not None
        return result_exists

    def get_result(self, query_hash: str, llm: str) -> str:
        cursor = self.conn.execute('''
            SELECT result FROM query_cache WHERE query_hash = ? AND llm = ?
        ''', (query_hash, llm))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_result(self, query_hash: str, query: str, result: str, llm: str) -> None:
        with self.conn:
            self.conn.execute('''
                INSERT OR REPLACE INTO query_cache (query_hash, llm, query, result)
                VALUES (?, ?, ?, ?)
            ''', (query_hash, llm, query, result))

    def __del__(self):
        self.conn.close()


class LLMCachePool:
    """
    Singleton class to manage the LLM caches in order to avoid recreating them.
    """

    _caches: Dict[str, LLMHashCache] = dict()

    @classmethod
    def get(cls, temperature: float, max_tokens: int):
        name: str = f'query_temperature-{round(temperature, 2)}_tokens-{max_tokens}_cache.db'
        if name not in cls._caches:
            cls._caches[name] = LLMHashCache(db_name=name)

        return cls._caches[name]

    @classmethod
    def get_by_name(cls, name: str):
        if name not in cls._caches:
            cls._caches[name] = LLMHashCache(db_name=name)

        return cls._caches[name]
