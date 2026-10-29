"""OSV.dev's list of known malicious packages (the MAL- entries from the OpenSSF malicious-packages project)."""

import httpx

QUERY_URL = "https://api.osv.dev/v1/query"
ECOSYSTEMS = {"npm": "npm", "pypi": "PyPI"}


async def malicious_ids(client: httpx.AsyncClient, ecosystem: str, name: str, version: str | None) -> list[str]:
    """MAL- IDs for this version, or for any version when `version` is None (e.g. a package npm already deleted)."""
    body: dict = {"package": {"ecosystem": ECOSYSTEMS[ecosystem], "name": name}}
    if version:
        body["version"] = version
    response = await client.post(QUERY_URL, json=body)
    response.raise_for_status()
    return sorted(v["id"] for v in response.json().get("vulns", []) if v.get("id", "").startswith("MAL-"))
