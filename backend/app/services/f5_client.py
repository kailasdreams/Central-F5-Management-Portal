"""
Thin wrapper around F5 BIG-IP iControl REST API.
Handles auth, base requests, and UCS backup lifecycle (create/list/download/delete).
"""
import time
import requests
from typing import Optional
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class F5ClientError(Exception):
    pass


class F5Client:
    def __init__(self, host: str, port: int, username: str, password: str, timeout: int = 15):
        self.base_url = f"https://{host}:{port}/mgmt"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = False
        self.timeout = timeout

    # ---------- Generic ----------
    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.exceptions.RequestException as e:
            raise F5ClientError(f"Connection error to {url}: {e}")
        if resp.status_code >= 400:
            raise F5ClientError(f"{method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        return resp

    # ---------- Health / Info ----------
    def test_connection(self) -> dict:
        resp = self._request("GET", "/tm/sys/version")
        data = resp.json()
        entries = data.get("entries", {})
        version = None
        hostname = None
        for _, v in entries.items():
            nested = v.get("nestedStats", {}).get("entries", {})
            if "Version" in nested:
                version = nested["Version"].get("description")
        hn_resp = self._request("GET", "/tm/sys/global-settings")
        hostname = hn_resp.json().get("hostname")
        return {"reachable": True, "hostname": hostname, "version": version}

    # ---------- UCS Backup ----------
    def create_ucs(self, filename: str) -> dict:
        """Kick off an async UCS save task."""
        body = {"command": "save", "name": filename}
        resp = self._request("POST", "/tm/sys/ucs", json=body)
        return resp.json()

    def get_ucs_task_status(self) -> list:
        resp = self._request("GET", "/tm/sys/ucs")
        return resp.json().get("items", [])

    def wait_for_ucs(self, filename: str, poll_interval: int = 5, max_wait: int = 600) -> bool:
        """Poll until the named UCS file appears in the ucs list (BIG-IP has no
        granular task-status endpoint for UCS save; presence in listing = done)."""
        elapsed = 0
        while elapsed < max_wait:
            items = self.get_ucs_task_status()
            for item in items:
                if filename in item.get("apiRawValues", {}).get("filename", "") or filename in str(item):
                    return True
            time.sleep(poll_interval)
            elapsed += poll_interval
        return False

    def download_ucs(self, filename: str, dest_path: str) -> int:
        """Download a UCS file via the iControl REST bulk file-transfer endpoint.
        Returns bytes written."""
        url = f"{self.base_url}/shared/file-transfer/ucs-downloads/{filename}"
        chunk_size = 512 * 1024
        total = 0
        headers = {"Content-Type": "application/octet-stream"}
        with self.session.get(url, headers=headers, stream=True, timeout=60, verify=False) as resp:
            if resp.status_code >= 400:
                raise F5ClientError(f"UCS download failed: HTTP {resp.status_code}")
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
        return total

    def delete_ucs(self, filename: str):
        self._request("DELETE", f"/tm/sys/ucs/{filename}")

    # ---------- Bash passthrough (for structured command runner, read-only friendly) ----------
    def run_bash(self, command: str) -> str:
        body = {"command": "run", "utilCmdArgs": f"-c \"{command}\""}
        resp = self._request("POST", "/tm/util/bash", json=body)
        return resp.json().get("commandResult", "")
