from __future__ import annotations

from typing import Any

import ollama


def _check_ollama_client(client: Any) -> None:
    if hasattr(client, "check"):
        client.check()
    elif hasattr(client, "ps"):
        client.ps()
    else:
        raise RuntimeError("Ollama client does not support health checks")


class OllamaEmbeddingClient:
    def __init__(self, *, client: Any, model: str) -> None:
        if not model or not model.strip():
            raise ValueError("Ollama embed model must be configured")
        self.model = model
        self._client = client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._client.embed(model=self.model, input=texts)
        except Exception as exc:
            raise RuntimeError("Failed to fetch embeddings from Ollama") from exc

        try:
            embeddings = response["embeddings"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed embeddings response") from exc

        return [[float(value) for value in vector] for vector in embeddings]

    def check(self) -> None:
        _check_ollama_client(self._client)


class OllamaGenerationClient:
    def __init__(self, *, client: Any, model: str) -> None:
        if not model or not model.strip():
            raise ValueError("Ollama generation model must be configured")
        self.model = model
        self._client = client

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        except Exception as exc:
            raise RuntimeError("Failed to generate response from Ollama") from exc

        try:
            generated_text = response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed generation response") from exc

        return str(generated_text)

    def check(self) -> None:
        _check_ollama_client(self._client)
