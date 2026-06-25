"""Monthly tenant SLA report generator (stub).

Full implementation lands in feat/tenant-sla-reports (KAN-37).
"""
from __future__ import annotations

import click
import structlog

log = structlog.get_logger(__name__)


@click.command()
@click.option("--tenant", required=True, help="Tenant id, e.g. oxagon-terminals")
@click.option("--month", required=True, help="Report month, YYYY-MM")
def main(tenant: str, month: str) -> None:
    """Generate the monthly SLA report for a tenant."""
    log.info("report.start", tenant=tenant, month=month)
    # TODO(KAN-37): query Postgres + Looker, render Jinja template, write PDF, upload to S3.
    log.info("report.todo", note="See feat/tenant-sla-reports")


if __name__ == "__main__":
    main()
