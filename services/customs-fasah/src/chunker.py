"""Manifest chunker.

Workaround for the Fasah pre-clearance gateway timing out on vessels
larger than ~ 8000 TEU. Empirically the Fasah edge times out at ~ 60s,
and the gateway can't ingest manifests above ~ 2500 containers in that
budget regardless of payload size.

Strategy:

1. Split the manifest by container count, never exceeding `max_containers`
   per chunk.
2. Tag every chunk with a deterministic `chunkIndex` (1..N) and `chunkTotal`
   so Fasah can stitch them server-side. The combination of vesselImo +
   voyageNumber + chunkIndex is unique per chunk and idempotent on retry.
3. Keep the manifest header (vessel, voyage, port, importer) identical
   across all chunks — only the `containers` array differs.

Tracks KAN-53.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any, Iterator


class ManifestChunker:
    """Splits a Fasah PreClearanceManifest into N submission-sized chunks."""

    def __init__(self, max_containers: int = 2500):
        if max_containers < 1:
            raise ValueError("max_containers must be >= 1")
        self.max_containers = max_containers

    def chunk(self, manifest: dict[str, Any]) -> Iterator[dict[str, Any]]:
        containers = list(manifest.get("containers", []))
        if not containers:
            # nothing to send, but Fasah requires a non-empty payload —
            # callers should filter empty manifests before calling.
            yield manifest
            return

        # Deterministic order so retries hash identically (KAN-53 idempotency).
        containers.sort(key=lambda c: c["containerNumber"])

        total_chunks = (len(containers) + self.max_containers - 1) // self.max_containers
        manifest_id = _stable_manifest_id(manifest)

        for idx in range(total_chunks):
            start = idx * self.max_containers
            end = start + self.max_containers
            chunk = copy.copy(manifest)  # shallow: don't deep-copy containers list
            chunk["containers"] = containers[start:end]
            chunk["chunkIndex"] = idx + 1
            chunk["chunkTotal"] = total_chunks
            chunk["chunkGroupId"] = manifest_id
            yield chunk


def _stable_manifest_id(manifest: dict[str, Any]) -> str:
    """Deterministic id used by Fasah to stitch chunks of the same manifest.

    Hashes vessel + voyage + port + a sorted container-number fingerprint so
    that retries of the *same* manifest produce the same group id, but a
    *different* manifest (even for the same vessel/voyage) does not collide.
    """
    h = hashlib.sha256()
    h.update(manifest.get("vesselImo", "").encode())
    h.update(b"|")
    h.update(manifest.get("voyageNumber", "").encode())
    h.update(b"|")
    h.update(manifest.get("portOfDischarge", "").encode())
    h.update(b"|")
    cnums = sorted(c["containerNumber"] for c in manifest.get("containers", []))
    h.update(",".join(cnums).encode())
    return h.hexdigest()[:24]
