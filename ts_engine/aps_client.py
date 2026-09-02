import base64
import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests

APS_BASE = "https://developer.api.autodesk.com"


class APSConfigError(RuntimeError):
    pass


class APSClient:
    """Minimal Autodesk Platform Services client for DWG/RVT ingestion.

    Uses OAuth v2, OSS v2 signed S3 upload, and Model Derivative API.
    Credentials are read from APS_CLIENT_ID and APS_CLIENT_SECRET.
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None, bucket_key: str | None = None):
        self.client_id = client_id or os.getenv("APS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("APS_CLIENT_SECRET")
        self.bucket_key = (bucket_key or os.getenv("APS_BUCKET_KEY") or "ts-ai-tender-engine").lower().replace("_", "-")
        if not self.client_id or not self.client_secret:
            raise APSConfigError("Missing APS_CLIENT_ID / APS_CLIENT_SECRET")
        self._token = None
        self._token_expiry = 0.0

    def _auth_header(self) -> dict[str, str]:
        raw = f"{self.client_id}:{self.client_secret}".encode()
        basic = base64.b64encode(raw).decode()
        return {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"}

    def token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = requests.post(
            f"{APS_BASE}/authentication/v2/token",
            headers=self._auth_header(),
            data={
                "grant_type": "client_credentials",
                "scope": "data:read data:write data:create bucket:create bucket:read",
            },
            timeout=30,
        )
        r.raise_for_status()
        payload = r.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + int(payload.get("expires_in", 3599))
        return self._token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}"}

    def ensure_bucket(self) -> None:
        # Bucket keys are globally unique. If the configured key is taken by another app,
        # user should provide APS_BUCKET_KEY with a unique value.
        r = requests.post(
            f"{APS_BASE}/oss/v2/buckets",
            headers={**self.headers(), "Content-Type": "application/json"},
            json={"bucketKey": self.bucket_key, "policyKey": "transient"},
            timeout=30,
        )
        if r.status_code in (200, 201, 409):
            return
        r.raise_for_status()

    def upload_file(self, path: str | Path) -> dict:
        path = Path(path)
        self.ensure_bucket()
        object_key = quote(path.name, safe="")
        signed = requests.get(
            f"{APS_BASE}/oss/v2/buckets/{self.bucket_key}/objects/{object_key}/signeds3upload",
            headers=self.headers(),
            params={"parts": 1},
            timeout=30,
        )
        signed.raise_for_status()
        signed_json = signed.json()
        urls = signed_json.get("urls") or []
        if not urls:
            raise RuntimeError(f"APS did not return a signed upload URL: {signed_json}")
        upload_key = signed_json["uploadKey"]

        with path.open("rb") as fh:
            up = requests.put(urls[0], data=fh, timeout=180)
            up.raise_for_status()

        finalize = requests.post(
            f"{APS_BASE}/oss/v2/buckets/{self.bucket_key}/objects/{object_key}/signeds3upload",
            headers={**self.headers(), "Content-Type": "application/json"},
            json={"uploadKey": upload_key},
            timeout=30,
        )
        finalize.raise_for_status()
        info = finalize.json()
        object_id = info.get("objectId") or f"urn:adsk.objects:os.object:{self.bucket_key}/{path.name}"
        urn = base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")
        return {"object_id": object_id, "urn": urn, "raw": info}

    def start_translation(self, urn: str) -> dict:
        # SVF2 is requested because it provides both visualization and metadata extraction.
        payload = {
            "input": {"urn": urn},
            "output": {"formats": [{"type": "svf2", "views": ["2d", "3d"]}]},
        }
        r = requests.post(
            f"{APS_BASE}/modelderivative/v2/designdata/job",
            headers={**self.headers(), "Content-Type": "application/json", "x-ads-force": "true"},
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def manifest(self, urn: str) -> dict:
        r = requests.get(
            f"{APS_BASE}/modelderivative/v2/designdata/{urn}/manifest",
            headers=self.headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def wait_until_ready(self, urn: str, timeout_seconds: int = 300, poll_seconds: int = 5) -> dict:
        deadline = time.time() + timeout_seconds
        last = {}
        while time.time() < deadline:
            last = self.manifest(urn)
            status = str(last.get("status", "")).lower()
            progress = str(last.get("progress", ""))
            if status == "success" or progress == "complete":
                return last
            if status in {"failed", "timeout"}:
                raise RuntimeError(f"APS translation failed: {json.dumps(last)[:1200]}")
            time.sleep(poll_seconds)
        raise TimeoutError("APS translation did not complete within the configured timeout")

    def metadata(self, urn: str) -> dict:
        r = requests.get(
            f"{APS_BASE}/modelderivative/v2/designdata/{urn}/metadata",
            headers=self.headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def properties(self, urn: str, guid: str) -> dict:
        r = requests.get(
            f"{APS_BASE}/modelderivative/v2/designdata/{urn}/metadata/{guid}/properties",
            headers=self.headers(),
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def ingest_model(self, path: str | Path, wait: bool = True) -> dict:
        uploaded = self.upload_file(path)
        self.start_translation(uploaded["urn"])
        manifest = self.wait_until_ready(uploaded["urn"]) if wait else {}
        md = self.metadata(uploaded["urn"]) if wait else {}
        views = md.get("data", {}).get("metadata", []) if md else []
        property_sets = []
        if wait:
            for view in views[:8]:  # cap for project; user can pick specific views later
                guid = view.get("guid")
                if guid:
                    try:
                        property_sets.append({"guid": guid, "name": view.get("name"), "properties": self.properties(uploaded["urn"], guid)})
                    except requests.HTTPError as exc:
                        property_sets.append({"guid": guid, "name": view.get("name"), "error": str(exc)})
        return {
            "source": str(path),
            "urn": uploaded["urn"],
            "object_id": uploaded["object_id"],
            "manifest": manifest,
            "metadata": md,
            "property_sets": property_sets,
        }
