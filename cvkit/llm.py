"""Talk to a model running on this computer (Ollama, LM Studio, llama.cpp). Nothing is sent anywhere else.

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


class _Local:
    """Shared by both connections: the local-only check and the JSON retry."""
    default_host = "http://localhost:11434"

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int = 600,
                 allow_remote: bool = False):
        self.model = model or os.environ.get("CVKIT_MODEL") or ""
        host = host or self._env_host() or self.default_host
        self.host = (host if "://" in host else f"http://{host}").rstrip("/")
        self.timeout = timeout
        if not allow_remote and urlparse(self.host).hostname not in LOCAL_HOSTS:
            raise ModelError(f"{self.host} is not on this computer; cvkit only sends CV text to a local model "
                             "(pass --allow-remote if that host is yours)")

    def _env_host(self) -> str | None:
        return None

    def _request(self, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.host + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise ModelError(f"{self.host} answered {e.code}: {e.read().decode(errors='replace')[:200]}") from e
        except urllib.error.URLError as e:
            raise ModelError(f"cannot reach a model server at {self.host}; is it running? ({e.reason})") from e

    def _post(self, path: str, body: dict) -> dict:
        return self._request(path, body)

    def _chat(self, system: str, user: str, schema: dict) -> str:
        raise NotImplementedError

    def json(self, system: str, user: str, schema: dict) -> dict:
        """One question, one answer shaped by `schema`. Temperature 0 so the same input gives the same answer.

        Small models sometimes ignore the schema and answer in plain text; then it asks once more, with the
        schema written into the instructions, before giving up."""
        for attempt in range(2):
            sys_text = system if attempt == 0 else (
                system + "\n\nReply with JSON only, no other text, matching this JSON schema:\n" + json.dumps(schema))
            parsed = _parse(self._chat(sys_text, user, schema))
            if isinstance(parsed, dict):
                return parsed
        raise ModelError("the model did not return valid JSON twice; try a larger model")


class Ollama(_Local):
    """Ollama's own API (default http://localhost:11434, model gemma4)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.model = self.model or DEFAULT_MODEL

    def _env_host(self):
        return os.environ.get("OLLAMA_HOST")

    def _chat(self, system, user, schema):
        reply = self._post("/api/chat", {
            "model": self.model, "stream": False, "format": schema,
            "options": {"temperature": 0, "num_ctx": 16384},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        return reply.get("message", {}).get("content", "")


class OpenAICompatible(_Local):
    """Any local server with an OpenAI-style /v1/chat/completions: LM Studio (default http://localhost:1234),
    llama.cpp's llama-server (http://localhost:8080), vLLM, Ollama's /v1. Without --model it uses the first model
    the server lists."""
    default_host = "http://localhost:1234"

    def _env_host(self):
        return os.environ.get("CVKIT_OPENAI_HOST")

    def _pick_model(self) -> str:
        if not self.model:
            models = self._request("/v1/models").get("data", [])
            chat = [m["id"] for m in models if "embed" not in m["id"].lower()]
            if not chat:
                raise ModelError(f"{self.host} lists no models; load one first (in LM Studio: lms load <model>)")
            self.model = chat[0]
        return self.model

    def _chat(self, system, user, schema):
        reply = self._post("/v1/chat/completions", {
            "model": self._pick_model(), "temperature": 0, "stream": False,
            "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        choices = reply.get("choices") or [{}]
        return (choices[0].get("message") or {}).get("content") or ""


APIS = {"ollama": ("Ollama", None), "lmstudio": ("OpenAICompatible", "http://localhost:1234"),
        "llamacpp": ("OpenAICompatible", "http://localhost:8080"), "openai": ("OpenAICompatible", None)}


def connect(api: str | None = None, model: str | None = None, host: str | None = None, allow_remote: bool = False):
    """api: ollama (default), lmstudio, llamacpp, or openai (any OpenAI-style server; give --host)."""
    api = api or os.environ.get("CVKIT_API") or "ollama"
    if api not in APIS:
        raise ModelError(f"unknown --api {api!r}; choose from {', '.join(APIS)}")
    name, preset = APIS[api]
    return globals()[name](model, host or preset, allow_remote=allow_remote)


def _parse(text: str):
    """The JSON object in `text`, also when the model wrapped it in a code fence or a sentence."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None
