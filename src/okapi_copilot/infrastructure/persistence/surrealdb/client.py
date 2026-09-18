"""
SurrealDB connection lifecycle wrapper.

A single, lazily-connected client shared by all SurrealDB-backed
repository adapters. Kept deliberately thin: connection/auth/namespace
selection only — no query logic lives here.

NOTE (honesty, per Document 11 Section 6 CAPABILITY STATUS): this class
has not been exercised against a running SurrealDB server in this
codebase's test suite. There is no SurrealDB instance reachable from
the environment this code was developed in. Treat connectivity as
UNVERIFIED until it has been run against `docker compose up surrealdb`
or a real deployment. The query-construction and row-mapping logic in
`membership_repository.py` IS unit-tested (against a fake client), but
that does not verify wire-protocol compatibility with a real server.
"""

from __future__ import annotations

from surrealdb import AsyncSurrealDB


class SurrealDbClient:
    def __init__(
        self,
        *,
        url: str,
        namespace: str,
        database: str,
        username: str = "",
        password: str = "",
    ) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._username = username
        self._password = password
        self._connection: AsyncSurrealDB | None = None

    async def connect(self) -> AsyncSurrealDB:
        if self._connection is not None:
            return self._connection

        connection = AsyncSurrealDB(self._url)
        await connection.connect()
        if self._username:
            await connection.sign_in(self._username, self._password)
        await connection.use(self._namespace, self._database)
        self._connection = connection
        return connection

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
