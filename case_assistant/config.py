"""Settings and the local-only guard.

Everything this app talks to must live on the firm's own hardware. The guard
refuses to start if the model server points anywhere that isn't loopback or a
private network address, unless someone deliberately sets CA_ALLOW_REMOTE=1.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    chat_model: str
    embed_model: str
    knowledge_dir: Path
    data_dir: Path
    allow_remote: bool
    top_k: int

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def audit_path(self) -> Path:
        return self.data_dir / "audit.jsonl"


def load_settings() -> Settings:
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        chat_model=os.getenv("CA_CHAT_MODEL", "llama3.1:8b"),
        embed_model=os.getenv("CA_EMBED_MODEL", "nomic-embed-text"),
        knowledge_dir=Path(os.getenv("CA_KNOWLEDGE_DIR", ROOT / "knowledge_base")),
        data_dir=Path(os.getenv("CA_DATA_DIR", ROOT / "data")),
        allow_remote=os.getenv("CA_ALLOW_REMOTE", "0") == "1",
        top_k=int(os.getenv("CA_TOP_K", "4")),
    )


class RemoteEndpointError(RuntimeError):
    """Raised when the model server is not on local or private infrastructure."""


def is_local_host(url: str) -> bool:
    host = urlparse(url if "://" in url else f"http://{url}").hostname or ""
    if host in {"localhost"}:
        return True
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False
    return bool(addresses) and all(
        ipaddress.ip_address(a).is_loopback or ipaddress.ip_address(a).is_private
        for a in addresses
    )


def enforce_local(settings: Settings) -> None:
    if settings.allow_remote:
        return
    if not is_local_host(settings.ollama_host):
        raise RemoteEndpointError(
            f"OLLAMA_HOST={settings.ollama_host} is not on this machine or a private "
            "network. Case data must stay on firm hardware. Set CA_ALLOW_REMOTE=1 only "
            "if you have approved that server."
        )
