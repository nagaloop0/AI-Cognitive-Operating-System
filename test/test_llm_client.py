"""
Unit tests for the local LLM client.
Every HTTP answer is faked with httpx.MockTransport, so Ollama does not need to run.
Run: venv/bin/python -m pytest test/test_llm_client.py -v
"""
import json
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.llm_client import LLMClient, LLMResponseError, LLMTimeoutError, LLMUnavailableError


def client_answering(handler) -> LLMClient:
    return LLMClient(base_url="http://ollama.test", model="test-model", transport=httpx.MockTransport(handler))


def chat_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}, "done": True})


def test_text_reply_is_returned():
    client = client_answering(lambda request: chat_reply("Hello there"))

    assert client.chat([{"role": "user", "content": "hi"}]) == "Hello there"


def test_request_sends_model_messages_and_no_streaming():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return chat_reply("ok")

    client_answering(handler).chat([{"role": "user", "content": "hi"}])

    assert seen["model"] == "test-model"
    assert seen["messages"] == [{"role": "user", "content": "hi"}]
    assert seen["stream"] is False
    assert "format" not in seen


def test_json_schema_is_sent_and_reply_is_parsed():
    schema = {"type": "object", "properties": {"mood": {"type": "string"}}}
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return chat_reply('{"mood": "focused"}')

    reply = client_answering(handler).chat([{"role": "user", "content": "mood?"}], json_schema=schema)

    assert seen["format"] == schema
    assert reply == {"mood": "focused"}


def test_broken_json_raises_response_error():
    client = client_answering(lambda request: chat_reply("{not json"))

    with pytest.raises(LLMResponseError, match="valid JSON"):
        client.chat([{"role": "user", "content": "x"}], json_schema={"type": "object"})


def test_server_down_raises_unavailable_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(LLMUnavailableError, match="ollama serve"):
        client_answering(handler).chat([{"role": "user", "content": "x"}])


def test_timeout_raises_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(LLMTimeoutError):
        client_answering(handler).chat([{"role": "user", "content": "x"}])


def test_missing_model_explains_how_to_pull_it():
    client = client_answering(lambda request: httpx.Response(404, json={"error": "model not found"}))

    with pytest.raises(LLMResponseError, match="ollama pull test-model"):
        client.chat([{"role": "user", "content": "x"}])


def test_server_error_raises_response_error():
    client = client_answering(lambda request: httpx.Response(500, text="boom"))

    with pytest.raises(LLMResponseError, match="HTTP 500"):
        client.chat([{"role": "user", "content": "x"}])


def test_embed_returns_one_vector_per_text():
    client = client_answering(lambda request: httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]}))

    assert client.embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_with_wrong_count_raises():
    client = client_answering(lambda request: httpx.Response(200, json={"embeddings": [[0.1]]}))

    with pytest.raises(LLMResponseError):
        client.embed(["a", "b"])
