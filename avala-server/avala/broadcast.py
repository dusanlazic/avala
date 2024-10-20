import psycopg2
from broadcaster import Broadcast

from .config import config

postgres_url = config.database.dsn()


class PostgresEmitter:
    """
    This class is responsible for emitting notifications to the Postgres database
    synchronosuly using pg_notify.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn = None

    def connect(self):
        self._conn = psycopg2.connect(self._dsn)
        self._conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    def disconnect(self):
        if self._conn:
            self._conn.close()

    def emit(self, channel: str, message: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute("SELECT pg_notify(%s, %s);", (channel, message))


broadcast = Broadcast(postgres_url)
emitter = PostgresEmitter(postgres_url)
