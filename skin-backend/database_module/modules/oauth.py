import time

from ..core import BaseDB


class OAuthModule:
    def __init__(self, db: BaseDB):
        self.db = db

    async def list_clients(self) -> list[dict]:
        async with self.db.get_conn() as conn:
            async with conn.execute(
                """
                SELECT app_id, client_name, redirect_uri, created_at, updated_at
                FROM oauth_clients
                ORDER BY app_id ASC
                """
            ) as cur:
                rows = await cur.fetchall()
                return [
                    {
                        "app_id": row[0],
                        "client_name": row[1],
                        "redirect_uri": row[2],
                        "created_at": row[3],
                        "updated_at": row[4],
                    }
                    for row in rows
                ]

    async def get_client(self, app_id: int) -> dict | None:
        async with self.db.get_conn() as conn:
            async with conn.execute(
                """
                SELECT app_id, client_name, client_secret_hash, redirect_uri, created_at, updated_at
                FROM oauth_clients
                WHERE app_id=?
                """,
                (app_id,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                return {
                    "app_id": row[0],
                    "client_name": row[1],
                    "client_secret_hash": row[2],
                    "redirect_uri": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                }

    async def create_client(self, client_name: str, secret_hash: str, redirect_uri: str) -> int:
        now = int(time.time() * 1000)
        async with self.db.get_conn() as conn:
            cur = await conn.execute(
                """
                INSERT INTO oauth_clients (client_name, client_secret_hash, redirect_uri, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_name, secret_hash, redirect_uri, now, now),
            )
            await conn.commit()
            return cur.lastrowid

    async def update_client(self, app_id: int, client_name: str, redirect_uri: str) -> bool:
        now = int(time.time() * 1000)
        async with self.db.get_conn() as conn:
            cur = await conn.execute(
                """
                UPDATE oauth_clients
                SET client_name=?, redirect_uri=?, updated_at=?
                WHERE app_id=?
                """,
                (client_name, redirect_uri, now, app_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def update_client_secret(self, app_id: int, secret_hash: str) -> bool:
        now = int(time.time() * 1000)
        async with self.db.get_conn() as conn:
            cur = await conn.execute(
                """
                UPDATE oauth_clients
                SET client_secret_hash=?, updated_at=?
                WHERE app_id=?
                """,
                (secret_hash, now, app_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def delete_client(self, app_id: int):
        async with self.db.get_conn() as conn:
            await conn.execute("DELETE FROM oauth_codes WHERE app_id=?", (app_id,))
            await conn.execute("DELETE FROM oauth_tokens WHERE app_id=?", (app_id,))
            await conn.execute("DELETE FROM oauth_clients WHERE app_id=?", (app_id,))
            await conn.commit()

    async def create_authorization_code(
        self,
        code: str,
        app_id: int,
        user_id: str,
        redirect_uri: str,
        scope: str,
        expires_at: int,
    ):
        now = int(time.time() * 1000)
        async with self.db.get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO oauth_codes (code, app_id, user_id, redirect_uri, scope, expires_at, created_at, used)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (code, app_id, user_id, redirect_uri, scope, expires_at, now),
            )
            await conn.commit()

    async def get_authorization_code(self, code: str) -> dict | None:
        async with self.db.get_conn() as conn:
            async with conn.execute(
                """
                SELECT code, app_id, user_id, redirect_uri, scope, expires_at, created_at, used
                FROM oauth_codes
                WHERE code=?
                """,
                (code,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                return {
                    "code": row[0],
                    "app_id": row[1],
                    "user_id": row[2],
                    "redirect_uri": row[3],
                    "scope": row[4],
                    "expires_at": row[5],
                    "created_at": row[6],
                    "used": row[7],
                }

    async def mark_code_used(self, code: str):
        async with self.db.get_conn() as conn:
            await conn.execute("UPDATE oauth_codes SET used=1 WHERE code=?", (code,))
            await conn.commit()

    async def create_access_token(
        self,
        access_token: str,
        refresh_token: str,
        app_id: int,
        user_id: str,
        scope: str,
        expires_at: int,
    ):
        now = int(time.time() * 1000)
        async with self.db.get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO oauth_tokens (access_token, refresh_token, app_id, user_id, scope, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (access_token, refresh_token, app_id, user_id, scope, expires_at, now),
            )
            await conn.commit()

    async def get_access_token(self, access_token: str) -> dict | None:
        async with self.db.get_conn() as conn:
            async with conn.execute(
                """
                SELECT access_token, refresh_token, app_id, user_id, scope, expires_at, created_at
                FROM oauth_tokens
                WHERE access_token=?
                """,
                (access_token,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "app_id": row[2],
                    "user_id": row[3],
                    "scope": row[4],
                    "expires_at": row[5],
                    "created_at": row[6],
                }
