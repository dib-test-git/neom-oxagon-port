"""Monthly tenant SLA report generator.

Pulls dwell, customs, and gate metrics for a tenant over a calendar
month, renders a per-tenant PDF via Jinja + WeasyPrint, and uploads it
to the per-tenant S3 bucket. Also pushes the dashboard URL to the
tenant portal so they can drill in via Looker.

Tracks KAN-37. DRAFT — pending Looker SDK upgrade (looker-sdk 24.18)
landing in `infra/`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import boto3
import click
import psycopg
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from looker_sdk import init40
from weasyprint import HTML

log = structlog.get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class SlaMetrics:
    tenant_id: str
    month: str
    container_count: int
    avg_dwell_hours: float
    p95_dwell_hours: float
    gate_p95_turn_minutes: float
    customs_p95_lead_hours: float
    yard_move_accuracy: float
    looker_dashboard_url: str


METRIC_QUERY = """
WITH window AS (
  SELECT *
  FROM dwell_windows
  WHERE tenant_id = %(tenant)s
    AND gate_out_at >= %(start)s
    AND gate_out_at <  %(end)s
)
SELECT
  count(*) AS container_count,
  avg(extract(epoch FROM (gate_out_at - gate_in_at)) / 3600.0)::numeric(8,2) AS avg_dwell_hours,
  percentile_cont(0.95) WITHIN GROUP (
    ORDER BY extract(epoch FROM (gate_out_at - gate_in_at)) / 3600.0
  )::numeric(8,2) AS p95_dwell_hours
FROM window;
"""


def fetch_metrics(conn: psycopg.Connection, tenant_id: str, month: str) -> SlaMetrics:
    start = date.fromisoformat(f"{month}-01")
    end = date(start.year + (start.month // 12), (start.month % 12) + 1, 1)
    with conn.cursor() as cur:
        cur.execute(METRIC_QUERY, dict(tenant=tenant_id, start=start, end=end))
        count, avg_h, p95_h = cur.fetchone()
    # Stub: turn-time, customs and yard accuracy currently from Looker;
    # we'll wire those once the SDK upgrade lands.
    return SlaMetrics(
        tenant_id=tenant_id,
        month=month,
        container_count=count or 0,
        avg_dwell_hours=float(avg_h or 0),
        p95_dwell_hours=float(p95_h or 0),
        gate_p95_turn_minutes=0.0,
        customs_p95_lead_hours=0.0,
        yard_move_accuracy=0.0,
        looker_dashboard_url=f"https://looker.neom.com/dashboards/tenant-sla?tenant={tenant_id}&month={month}",
    )


def render_pdf(metrics: SlaMetrics) -> bytes:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("sla_report.html.j2")
    html = tpl.render(m=metrics)
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def upload(pdf: bytes, tenant_id: str, month: str) -> str:
    s3 = boto3.client("s3", region_name="me-south-1")
    bucket = f"neom-oxagon-tenant-{tenant_id}"
    key = f"sla-reports/{month}.pdf"
    s3.put_object(Bucket=bucket, Key=key, Body=pdf, ContentType="application/pdf")
    return f"s3://{bucket}/{key}"


def push_looker_view(metrics: SlaMetrics) -> None:
    sdk = init40()
    # Stub: real implementation refreshes a per-tenant Looker board.
    _ = sdk.me()
    log.info("looker.push.stub", tenant=metrics.tenant_id, month=metrics.month)


@click.command()
@click.option("--tenant", required=True, help="Tenant id, e.g. oxagon-terminals")
@click.option("--month", required=True, help="Report month, YYYY-MM")
def main(tenant: str, month: str) -> None:
    conn = psycopg.connect(os.environ["POSTGRES_URL"])
    try:
        metrics = fetch_metrics(conn, tenant, month)
    finally:
        conn.close()

    pdf = render_pdf(metrics)
    s3_uri = upload(pdf, tenant, month)
    push_looker_view(metrics)
    log.info("report.done", tenant=tenant, month=month, s3=s3_uri)


if __name__ == "__main__":
    main()
