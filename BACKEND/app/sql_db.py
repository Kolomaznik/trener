"""Async PostgreSQL pool — singleton mirror of the Motor client in ``app/db.py``.

Pool is opened lazily on first use so importing this module doesn't bind to
a running asyncio loop. The lazy-open behavior mirrors how ``_client()`` in
``app/db.py`` defers connection until a handler runs.

If pool startup latency on the first request ever becomes a problem, wire
this into a FastAPI ``lifespan`` and open the pool at boot. Until then,
``get_pool`` covers the case fine.
"""

from functools import lru_cache

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import settings


@lru_cache(maxsize=1)
def _pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=settings.database_url,
        kwargs={"row_factory": dict_row},
        open=False,
        min_size=1,
        max_size=10,
    )


async def get_pool() -> AsyncConnectionPool:
    pool = _pool()
    if pool.closed:
        await pool.open()
    return pool
