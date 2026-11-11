"""Transport for the private company OpenAI-compatible gateway.

The gateway is reached by private IP but routes requests by its virtual Host.
It must therefore neither inherit process proxy settings nor replace the
configured Host header.
"""

from __future__ import annotations

from typing import Any

import requests


class CompanyGatewayTransport:
    """A requests transport isolated from HTTP(S)/ALL proxy environment variables."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        # This is intentionally per-client: callers do not need NO_PROXY set.
        self.session.trust_env = False

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
        timeout: int,
    ) -> requests.Response:
        return self.session.request(method, url, headers=headers, json=json, timeout=timeout)
