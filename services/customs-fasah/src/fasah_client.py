"""Thin async client for the Saudi Customs Fasah REST API."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger(__name__)


class FasahError(RuntimeError):
    """Raised for non-2xx Fasah responses we don't intend to retry."""


class FasahTransientError(RuntimeError):
    """Retryable Fasah error (5xx, 429, network)."""


@dataclass
class FasahCredentials:
    base_url: str
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> "FasahCredentials":
        return cls(
            base_url=os.environ.get("FASAH_BASE_URL", "https://api.fasah.sa/customs/v2"),
            client_id=os.environ["FASAH_CLIENT_ID"],
            client_secret=os.environ["FASAH_CLIENT_SECRET"],
        )


class FasahClient:
    """Async client. One instance per worker process; share across requests."""

    # Production timeout was 30s; bumped to 120s for the > 8000 TEU workaround in KAN-53.
    DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)

    def __init__(self, creds: FasahCredentials, *, timeout: httpx.Timeout | None = None):
        self._creds = creds
        self._http = httpx.AsyncClient(
            base_url=creds.base_url,
            timeout=timeout or self.DEFAULT_TIMEOUT,
            headers={"User-Agent": "oxagon-customs/0.4"},
        )
        self._token: str | None = None
        self._token_exp: float = 0.0

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _auth_header(self) -> dict[str, str]:
        if not self._token or time.time() > self._token_exp - 60:
            resp = await self._http.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._creds.client_id,
                    "client_secret": self._creds.client_secret,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            self._token = body["access_token"]
            self._token_exp = time.time() + int(body.get("expires_in", 3600))
        return {"Authorization": f"Bearer {self._token}"}

    @retry(
        retry=retry_if_exception_type(FasahTransientError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def submit_preclearance(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """POST a single PreClearanceManifest. Returns the Fasah reference + status."""
        headers = await self._auth_header()
        try:
            resp = await self._http.post("/preclearance/manifests", json=manifest, headers=headers)
        except httpx.HTTPError as e:
            raise FasahTransientError(f"network: {e}") from e

        if resp.status_code in (502, 503, 504, 429):
            raise FasahTransientError(f"fasah {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise FasahError(f"fasah {resp.status_code}: {resp.text[:500]}")

        body = resp.json()
        log.info(
            "fasah.preclearance.submitted",
            vessel=manifest.get("vesselImo"),
            container_count=len(manifest.get("containers", [])),
            reference=body.get("fasahReferenceNumber"),
        )
        return body

    async def get_status(self, fasah_reference: str) -> dict[str, Any]:
        headers = await self._auth_header()
        resp = await self._http.get(f"/preclearance/manifests/{fasah_reference}", headers=headers)
        resp.raise_for_status()
        return resp.json()
