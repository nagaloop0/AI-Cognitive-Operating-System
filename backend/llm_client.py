"""
Small client for the local Ollama server (default http://localhost:11434).
All model calls stay on this Mac: activity data never goes to a cloud API.

Try it: venv/bin/python -m backend.llm_client "Say hello in 5 words"
"""
import json
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DEFAULT_TIMEOUT_SECONDS = 60.0


class LLMError(Exception):
    """Base class for every problem talking to the local model."""


class LLMUnavailableError(LLMError):
    """Ollama is not running or cannot be reached."""


class LLMTimeoutError(LLMError):
    """The model did not answer in time."""


class LLMResponseError(LLMError):
    """Ollama answered, but the answer is unusable (HTTP error, missing model, invalid JSON)."""


class LLMClient:
    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model: str = LLM_MODEL,
        embed_model: str = EMBED_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ):
        # `transport` lets tests plug in fake HTTP answers (httpx.MockTransport)
        self.base_url = base_url
        self.model = model
        self.embed_model = embed_model
        self._http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def chat(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str | dict[str, Any]:
        """Sends a conversation and returns the reply.
        Without a schema the reply is plain text; with a JSON schema Ollama is forced to answer
        in that shape and the parsed dict is returned."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_schema is not None:
            payload["format"] = json_schema

        content = self.chat_message(payload)["content"]
        if json_schema is None:
            return content
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"The model did not return valid JSON: {content[:200]!r}") from e

    def chat_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Low-level chat call: returns the raw assistant message (content and optional tool_calls)."""
        payload.setdefault("model", self.model)
        payload.setdefault("stream", False)
        data = self._post("/api/chat", payload)
        message = data.get("message")
        if not isinstance(message, dict) or "content" not in message:
            raise LLMResponseError(f"Unexpected answer from Ollama: {str(data)[:200]}")
        return message

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Turns each text into a vector (a list of numbers) with the embedding model."""
        if not texts:
            return []
        data = self._post("/api/embed", {"model": self.embed_model, "input": texts})
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise LLMResponseError("Ollama returned a wrong number of embeddings.")
        return embeddings

    def is_available(self) -> bool:
        try:
            return self._http.get("/").status_code == 200
        except httpx.HTTPError:
            return False

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.post(path, json=payload)
        except httpx.ConnectError as e:
            raise LLMUnavailableError(
                f"Ollama is not running at {self.base_url}. "
                "Start it with `ollama serve` or `brew services start ollama`."
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"No answer from the model within {self._http.timeout.read} s.") from e

        if response.status_code == 404:
            model = payload.get("model", self.model)
            raise LLMResponseError(f"Model '{model}' is not installed. Run `ollama pull {model}`.")
        if response.status_code >= 400:
            raise LLMResponseError(f"Ollama returned HTTP {response.status_code}: {response.text[:200]}")
        try:
            return response.json()
        except ValueError as e:
            raise LLMResponseError("Ollama returned a body that is not JSON.") from e


def get_llm_client() -> LLMClient:
    """FastAPI dependency; tests override it with a fake client."""
    return LLMClient()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Say hello in 5 words."
    try:
        print(LLMClient().chat([{"role": "user", "content": question}]))
    except LLMError as e:
        print(f"[LLM ERROR] {e}")
        sys.exit(1)
