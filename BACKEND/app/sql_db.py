"""Async PostgreSQL pool — singleton mirror of the Motor client in ``app/db.py``.

Pool is opened lazily on first use so importing this module doesn't bind to
a running asyncio loop. The lazy-open behavior mirrors how ``_client()`` in
``app/db.py`` defers connection until a handler runs.

If pool startup latency on the first request ever becomes a problem, wire
this into a FastAPI ``lifespan`` and open the pool at boot. Until then,
``get_pool`` covers the case fine.

Convenience helpers ``fetchall`` / ``fetchone`` / ``execute`` grab the
singleton pool internally so handler code stays terse:

    rows = await fetchall("SELECT … WHERE email = %s", (user.email,))

For multi-statement transactions, drop down to ``pool.connection()``
directly via ``get_pool()``.
"""

from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import settings

# Either positional (tuple/list) or named (dict) bind parameters; ``None`` runs
# the query with no params.
SqlParams = Sequence[Any] | Mapping[str, Any] | None


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


async def fetchall(query: Any, params: SqlParams = None) -> list[dict[str, Any]]:
    """Run ``query`` and return all rows as dicts (via the pool's ``dict_row`` factory)."""
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(query, params)
        return await cur.fetchall()


async def fetchone(query: Any, params: SqlParams = None) -> dict[str, Any] | None:
    """Run ``query`` and return the first row as a dict, or ``None`` if no row matched."""
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(query, params)
        return await cur.fetchone()


async def execute(query: Any, params: SqlParams = None) -> None:
    """Run ``query`` without returning any rows (INSERT/UPDATE/DELETE without RETURNING)."""
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(query, params)
