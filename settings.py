from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache

from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None, default: str) -> tuple[str, ...]:
    raw = value or default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_domain: str
    allowed_hosts: tuple[str, ...]
    session_secret_key: str
    session_cookie_name: str
    session_max_age_seconds: int
    session_secure_cookies: bool
    auth_admin_username: str
    auth_password_hash: str
    auth_dev_password: str
    login_max_attempts: int
    login_lockout_minutes: int

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development")
    auth_dev_password = os.getenv("AUTH_DEV_PASSWORD", "Admin123!!")
    auth_password_hash = os.getenv("AUTH_PASSWORD_HASH", "").strip()

    if not auth_password_hash:
        if app_env.lower() == "production":
            raise RuntimeError(
                "AUTH_PASSWORD_HASH es obligatorio en produccion. Genera uno fuerte antes de desplegar."
            )
        auth_password_hash = password_hasher.hash(auth_dev_password)

    session_secret_key = os.getenv("SESSION_SECRET_KEY", "").strip()
    if not session_secret_key:
        if app_env.lower() == "production":
            raise RuntimeError("SESSION_SECRET_KEY es obligatorio en produccion.")
        session_secret_key = secrets.token_urlsafe(32)

    app_domain = os.getenv("APP_DOMAIN", "127.0.0.1")
    return Settings(
        app_env=app_env,
        app_domain=app_domain,
        allowed_hosts=_parse_csv(
            os.getenv("APP_ALLOWED_HOSTS"),
            f"127.0.0.1,localhost,testserver,{app_domain}",
        ),
        session_secret_key=session_secret_key,
        session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "ediccc_session"),
        session_max_age_seconds=int(os.getenv("SESSION_MAX_AGE_SECONDS", "28800")),
        session_secure_cookies=_parse_bool(
            os.getenv("SESSION_SECURE_COOKIES"),
            default=app_env.lower() == "production",
        ),
        auth_admin_username=os.getenv("AUTH_ADMIN_USERNAME", "admin").strip(),
        auth_password_hash=auth_password_hash,
        auth_dev_password=auth_dev_password,
        login_max_attempts=int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")),
        login_lockout_minutes=int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15")),
    )
