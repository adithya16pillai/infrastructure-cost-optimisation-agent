from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agent.state import AgentState, Finding
from app.cloud.base import CloudClient
from app.models.enums import FindingType, ResourceType

logger = logging.getLogger(__name__)


def _created_days_ago(create_time: str | None) -> int | None:
    if not create_time:
        return None
    dt = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def detect(client: CloudClient, raw_data: dict) -> list[Finding]:
    findings: list[Finding] = []

    for d in raw_data.get("disks", []):
        if d["state"] != "available":
            continue

        rate = client.get_disk_gb_month_cost(d["disk_type"])
        monthly_cents = round(d["size_gb"] * rate * 100)
        findings.append(
            Finding(
                provider=client.provider,
                finding_type=FindingType.UNATTACHED_DISK.value,
                resource_type=ResourceType.DISK.value,
                resource_id=d["disk_id"],
                region=d["region"],
                estimated_monthly_savings_cents=monthly_cents,
                evidence={
                    "size_gb": d["size_gb"],
                    "disk_type": d["disk_type"],
                    "created_days_ago": _created_days_ago(d.get("create_time")),
                },
                title=f"Unattached disk {d['disk_id']} ({d['size_gb']} GB)",
                description=(
                    f"Disk {d['disk_id']} ({d['size_gb']} GB {d['disk_type']}) "
                    f"is in the 'available' state and attached to no instance. "
                    f"You are billed for it while it sits idle. Consider snapshotting "
                    f"then deleting it."
                ),
            )
        )
    return findings


def run(state: AgentState, client: CloudClient) -> dict:
    try:
        return {"unattached_disk_findings": detect(client, state["raw_data"])}
    except Exception as exc:  # noqa: BLE001
        logger.exception("unattached_disk detector failed")
        return {"unattached_disk_findings": [], "errors": [f"unattached_disk: {exc}"]}
