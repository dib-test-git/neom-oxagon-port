"""Dwell-window persistence and metric emission.

A dwell window is opened at GATE_IN and closed at GATE_OUT for the
same (tenant_id, container_number) pair. We store partial windows in
Postgres; on close, we compute the dwell duration and emit a metric.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import psycopg
import structlog

log = structlog.get_logger(__name__)


@dataclass
class DwellWindow:
    tenant_id: str
    container_number: str
    gate_in_at: datetime
    gate_out_at: Optional[datetime]
    yard_block: Optional[str]

    @property
    def dwell_seconds(self) -> Optional[int]:
        if self.gate_out_at is None:
            return None
        return int((self.gate_out_at - self.gate_in_at).total_seconds())


UPSERT_OPEN = """
INSERT INTO dwell_windows (tenant_id, container_number, gate_in_at, yard_block)
VALUES (%(tenant_id)s, %(container_number)s, %(gate_in_at)s, %(yard_block)s)
ON CONFLICT (tenant_id, container_number)
WHERE gate_out_at IS NULL
DO UPDATE SET gate_in_at = LEAST(dwell_windows.gate_in_at, EXCLUDED.gate_in_at);
"""

CLOSE_WINDOW = """
UPDATE dwell_windows
SET gate_out_at = %(gate_out_at)s
WHERE tenant_id = %(tenant_id)s
  AND container_number = %(container_number)s
  AND gate_out_at IS NULL
RETURNING gate_in_at, gate_out_at, yard_block;
"""


def open_window(conn: psycopg.Connection, tenant_id: str, container: str, at: datetime, yard_block: Optional[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(UPSERT_OPEN, dict(
            tenant_id=tenant_id, container_number=container, gate_in_at=at, yard_block=yard_block
        ))
    conn.commit()


def close_window(conn: psycopg.Connection, tenant_id: str, container: str, at: datetime) -> Optional[DwellWindow]:
    with conn.cursor() as cur:
        cur.execute(CLOSE_WINDOW, dict(
            tenant_id=tenant_id, container_number=container, gate_out_at=at
        ))
        row = cur.fetchone()
    conn.commit()
    if not row:
        log.warning("dwell.no_open_window", tenant=tenant_id, container=container)
        return None
    gate_in_at, gate_out_at, yard_block = row
    return DwellWindow(tenant_id, container, gate_in_at, gate_out_at, yard_block)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
