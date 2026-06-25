"""Manifest chunker.

Stub. The full chunking algorithm — needed to work around the Fasah
gateway timeout on vessels > 8000 TEU — is being delivered in
fix/fasah-chunked-submission (KAN-53).

For now, this just passes the manifest through unchanged.
"""
from __future__ import annotations

from typing import Any, Iterable


class ManifestChunker:
    def __init__(self, max_containers: int = 2500):
        self.max_containers = max_containers

    def chunk(self, manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
        # TODO(KAN-53): split by container count and tag each chunk with
        # a deterministic chunk index so Fasah can stitch them server-side.
        yield manifest
