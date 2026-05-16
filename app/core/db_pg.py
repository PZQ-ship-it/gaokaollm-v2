import os
import asyncio
import sys
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"

_pool: AsyncConnectionPool | None = None
_pool_loop: asyncio.AbstractEventLoop | None = None


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


async def get_pool() -> AsyncConnectionPool:
    global _pool, _pool_loop
    current_loop = asyncio.get_running_loop()
    if _pool is None or _pool.closed or _pool_loop is not current_loop:
        _pool = AsyncConnectionPool(
            conninfo=get_database_url(),
            kwargs={"row_factory": dict_row},
            open=False,
        )
        await _pool.open()
        _pool_loop = current_loop
    return _pool


async def fetch_query(query: str, *args: Any) -> list[dict[str, Any]]:
    if sys.platform == "win32":
        return await asyncio.to_thread(_fetch_query_sync, query, *args)
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, args)
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


def _fetch_query_sync(query: str, *args: Any) -> list[dict[str, Any]]:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


async def close_pool() -> None:
    global _pool, _pool_loop
    if _pool is not None:
        if not _pool.closed:
            await _pool.close()
        _pool = None
        _pool_loop = None
