"""Talk to a model running on this computer. Nothing is sent anywhere else.

Ollama by default (http://localhost:11434, model gemma4). Settings: CVKIT_MODEL, OLLAMA_HOST, or --model / --host.
Answers are forced into a JSON schema with Ollama's `format` option, so the model returns data, not prose.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_MODEL = "gemma4"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ModelError(RuntimeError):
    pass


class Ollama:
    def __init__(self, model: str | None = None, host: str | None = None, timeout: int = 600,
                 allow_remote: bool = False):
        self.model = model or os.environ.get("CVKIT_MODEL") or DEFAULT_MODEL
        host = host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
        self.host = host if "://" in host else f"http://{host}"
        self.timeout = timeout
        if not allow_remote and urlparse(self.host).hostname not in LOCAL_HOSTS:
            raise ModelError(f"{self.host} is not on this computer; cvkit only sends CV text to a local model "
                             "(pass --allow-remote if that host is yours)")

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(self.host + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise ModelError(f"Ollama answered {e.code}: {e.read().decode(errors='replace')[:200]}") from e
        except urllib.error.URLError as e:
            raise ModelError(f"cannot reach Ollama at {self.host}; is it running? ({e.reason})") from e

    def json(self, system: str, user: str, schema: dict) -> dict:
        """One question, one answer shaped by `schema`. Temperature 0 so the same input gives the same answer."""
        reply = self._post("/api/chat", {
            "model": self.model, "stream": False, "format": schema,
            "options": {"temperature": 0, "num_ctx": 16384},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        text = reply.get("message", {}).get("content", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ModelError("the model did not return valid JSON; try a larger model (--model gemma4:12b)") from e
