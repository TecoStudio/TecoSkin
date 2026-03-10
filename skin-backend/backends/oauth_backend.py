import hashlib
import secrets
import time
from urllib.parse import urlencode

from fastapi import HTTPException

from config_loader import Config
from database_module import Database


class OAuthBackend:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    def _normalize_redirect_uri(self, redirect_uri: str) -> str:
        if not redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri required")
        value = str(redirect_uri).strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            raise HTTPException(status_code=400, detail="redirect_uri must start with http:// or https://")
        return value

    def _hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def _make_secret(self) -> str:
        return secrets.token_urlsafe(36)

    def _make_code(self) -> str:
        return secrets.token_urlsafe(32)

    def _make_access_token(self) -> str:
        return secrets.token_urlsafe(40)

    def _make_refresh_token(self) -> str:
        return secrets.token_urlsafe(40)

    def _mask_secret(self, secret: str) -> str:
        if len(secret) <= 8:
            return "*" * len(secret)
        return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]

    async def list_apps(self) -> list[dict]:
        rows = await self.db.oauth.list_clients()
        return rows

    async def create_app(self, client_name: str, redirect_uri: str) -> dict:
        final_name = (client_name or "").strip()
        final_redirect_uri = self._normalize_redirect_uri(redirect_uri)
        secret = self._make_secret()
        app_id = await self.db.oauth.create_client(final_name, self._hash_secret(secret), final_redirect_uri)
        return {
            "app_id": app_id,
            "client_name": final_name,
            "redirect_uri": final_redirect_uri,
            "client_secret": secret,
            "client_secret_masked": self._mask_secret(secret),
        }

    async def update_app(self, app_id: int, client_name: str, redirect_uri: str):
        final_name = (client_name or "").strip()
        final_redirect_uri = self._normalize_redirect_uri(redirect_uri)
        updated = await self.db.oauth.update_client(app_id, final_name, final_redirect_uri)
        if not updated:
            raise HTTPException(status_code=404, detail="oauth app not found")
        return {"ok": True}

    async def reset_app_secret(self, app_id: int) -> dict:
        app = await self.db.oauth.get_client(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="oauth app not found")
        secret = self._make_secret()
        await self.db.oauth.update_client_secret(app_id, self._hash_secret(secret))
        return {
            "app_id": app_id,
            "client_secret": secret,
            "client_secret_masked": self._mask_secret(secret),
        }

    async def delete_app(self, app_id: int):
        app = await self.db.oauth.get_client(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="oauth app not found")
        await self.db.oauth.delete_client(app_id)
        return {"ok": True}

    async def admin_meta(self) -> dict:
        site_url = str(self.config.get("server.site_url", "")).rstrip("/")
        api_url = str(self.config.get("server.api_url", "")).rstrip("/")
        if not api_url:
            root_path = str(self.config.get("server.root_path", "")).rstrip("/")
            if site_url and root_path:
                api_url = site_url + root_path
            elif site_url:
                api_url = site_url
        sample_redirect = "https://your-app.example.com/oauth/callback"
        return {
            "authorize_endpoint": f"{site_url}/oauth/authorize" if site_url else "/oauth/authorize",
            "token_endpoint": f"{api_url}/oauth/token" if api_url else "/oauth/token",
            "userinfo_endpoint": f"{api_url}/oauth/userinfo" if api_url else "/oauth/userinfo",
            "sample_redirect_uri": sample_redirect,
        }

    async def build_authorize_preview(self, client_id: int, redirect_uri: str, state: str = "") -> dict:
        app = await self.db.oauth.get_client(client_id)
        if not app:
            raise HTTPException(status_code=400, detail="invalid client_id")

        final_redirect_uri = self._normalize_redirect_uri(redirect_uri)
        if final_redirect_uri != app["redirect_uri"]:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")

        return {
            "app_id": app["app_id"],
            "client_name": app["client_name"],
            "redirect_uri": app["redirect_uri"],
            "state": state or "",
        }

    def _build_redirect(self, redirect_uri: str, params: dict) -> str:
        query = urlencode(params)
        sep = "&" if "?" in redirect_uri else "?"
        return f"{redirect_uri}{sep}{query}"

    async def authorize_decision(
        self,
        user_id: str,
        client_id: int,
        redirect_uri: str,
        state: str,
        approved: bool,
        scope: str = "basic",
    ) -> dict:
        app = await self.db.oauth.get_client(client_id)
        if not app:
            raise HTTPException(status_code=400, detail="invalid client_id")

        final_redirect_uri = self._normalize_redirect_uri(redirect_uri)
        if final_redirect_uri != app["redirect_uri"]:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")

        if not approved:
            params = {"error": "access_denied"}
            if state:
                params["state"] = state
            return {"redirect_url": self._build_redirect(final_redirect_uri, params)}

        user = await self.db.user.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="user not found")

        code = self._make_code()
        now = int(time.time() * 1000)
        expires_at = now + 5 * 60 * 1000
        await self.db.oauth.create_authorization_code(
            code=code,
            app_id=client_id,
            user_id=user_id,
            redirect_uri=final_redirect_uri,
            scope=scope or "basic",
            expires_at=expires_at,
        )

        params = {"code": code}
        if state:
            params["state"] = state
        return {"redirect_url": self._build_redirect(final_redirect_uri, params)}

    async def exchange_code(
        self,
        grant_type: str,
        code: str,
        client_id: int,
        client_secret: str,
        redirect_uri: str,
    ) -> dict:
        if grant_type != "authorization_code":
            raise HTTPException(status_code=400, detail="unsupported grant_type")

        app = await self.db.oauth.get_client(client_id)
        if not app:
            raise HTTPException(status_code=400, detail="invalid client")

        if self._hash_secret(client_secret or "") != app["client_secret_hash"]:
            raise HTTPException(status_code=401, detail="invalid client")

        final_redirect_uri = self._normalize_redirect_uri(redirect_uri)
        auth_code = await self.db.oauth.get_authorization_code(code)
        if not auth_code:
            raise HTTPException(status_code=400, detail="invalid code")
        if auth_code["used"]:
            raise HTTPException(status_code=400, detail="code already used")

        now = int(time.time() * 1000)
        if now > int(auth_code["expires_at"]):
            raise HTTPException(status_code=400, detail="code expired")
        if int(auth_code["app_id"]) != int(client_id):
            raise HTTPException(status_code=400, detail="code client mismatch")
        if auth_code["redirect_uri"] != final_redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")

        await self.db.oauth.mark_code_used(code)

        access_token = self._make_access_token()
        refresh_token = self._make_refresh_token()
        expires_in = 7200
        expires_at = now + expires_in * 1000
        await self.db.oauth.create_access_token(
            access_token=access_token,
            refresh_token=refresh_token,
            app_id=client_id,
            user_id=auth_code["user_id"],
            scope=auth_code.get("scope") or "basic",
            expires_at=expires_at,
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": refresh_token,
            "scope": auth_code.get("scope") or "basic",
        }

    async def get_userinfo(self, access_token: str) -> dict:
        record = await self.db.oauth.get_access_token(access_token)
        if not record:
            raise HTTPException(status_code=401, detail="invalid token")

        now = int(time.time() * 1000)
        if now > int(record["expires_at"]):
            raise HTTPException(status_code=401, detail="token expired")

        user = await self.db.user.get_by_id(record["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="invalid token")

        return {
            "sub": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_admin": bool(user.is_admin),
            "app_id": record["app_id"],
            "scope": record.get("scope") or "basic",
        }
