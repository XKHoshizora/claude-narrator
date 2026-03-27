"""LRU file-based audio cache."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioCache:
    """File-based LRU audio cache."""

    def __init__(self, cache_dir: Path, max_size_mb: int = 50) -> None:
        self._dir = cache_dir
        self._max_bytes = max_size_mb * 1024 * 1024
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, engine: str, voice: str, lang: str, text: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{engine}_{voice}_{lang}_{text_hash}"

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.mp3"

    def get(self, engine: str, voice: str, lang: str, text: str) -> bytes | None:
        path = self._path(self._key(engine, voice, lang, text))
        if path.exists():
            path.touch()  # Update access time for LRU
            return path.read_bytes()
        return None

    def put(self, engine: str, voice: str, lang: str, text: str, audio: bytes) -> None:
        self._evict_if_needed(len(audio))
        path = self._path(self._key(engine, voice, lang, text))
        path.write_bytes(audio)

    def clear(self) -> None:
        for f in self._dir.glob("*.mp3"):
            f.unlink(missing_ok=True)

    def _evict_if_needed(self, incoming_bytes: int) -> None:
        files = sorted(self._dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in files) + incoming_bytes
        while total > self._max_bytes and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            oldest.unlink(missing_ok=True)
