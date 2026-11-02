"""Model clients. Both talk only to a local Ollama server.

The Fake* classes let the tests run with no model installed.
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ChatModel(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class OllamaEmbedder:
    def __init__(self, host: str, model: str):
        import ollama

        self._client = ollama.Client(host=host)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed(model=self.model, input=texts)["embeddings"]


class OllamaChat:
    def __init__(self, host: str, model: str):
        import ollama

        self._client = ollama.Client(host=host)
        self.name = model

    def complete(self, system: str, user: str) -> str:
        reply = self._client.chat(
            model=self.name,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            options={"temperature": 0.1},
        )
        return reply["message"]["content"]


class FakeEmbedder:
    """Bag-of-words hashing embedder. Deterministic and good enough for tests."""

    dims = 256

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self.dims
            for word in text.lower().split():
                word = word.strip(".,:;()[]\"'")
                if word:
                    vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class FakeChat:
    name = "fake-model"

    def complete(self, system: str, user: str) -> str:
        return "Based on the sources provided [1]."
