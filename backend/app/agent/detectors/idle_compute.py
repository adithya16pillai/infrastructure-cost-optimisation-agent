from __future__ import annotations

import logging

from app.agent.state import AgentState, Finding
from app.cloud.base import CloudClient
from app.config import settings
from app.models.enums import FindingType, ResourceType

logger = logging.getLogger(__name__)


def detect(client: CloudClient, raw_data: dict) -> list[Finding]:
    threshold = settings.idle_cpu_percent_threshold
    lookback = settings.idle_lookback_days
    findings: list[Finding] = []

    for inst in raw_data.get("compute_instances", []):
        if inst["state"] != "running":
            continue

        cpu = client.get_cpu_utilization(inst["instance_id"], days=lookback)
        if len(cpu) == 0:
            continue  # no data, can't conclude

        avg = sum(cpu) / len(cpu)
        if avg >= threshold:
            continue

        hourly = client.get_instance_hourly_cost(inst["instance_type"], inst["region"])
        if hourly <= 0:
            logger.info("idle_compute skip %s (no price)", inst["instance_id"])
            continue

        monthly_cents = round(hourly * 24 * 30 * 100)
        tags = inst.get("tags", {})
        name = tags.get("Name") or tags.get("name")
        findings.append(
            Finding(
                provider=client.provider,
                finding_type=FindingType.IDLE_COMPUTE.value,
                resource_type=ResourceType.COMPUTE.value,
                resource_id=inst["instance_id"],
                region=inst["region"],
                estimated_monthly_savings_cents=monthly_cents,
                evidence={
                    "avg_cpu_percent": round(avg, 2),
                    "days_observed": len(cpu),
                    "instance_type": inst["instance_type"],
                    "tags": tags,
                },
                title=f"Idle compute instance {inst['instance_id']} ({inst['instance_type']})",
                description=(
                    f"Instance '{name or inst['instance_id']}' "
                    f"({inst['instance_type']}) averaged {avg:.1f}% CPU over the last "
                    f"{len(cpu)} days, below the {threshold:.0f}% idle threshold. "
                    f"Consider stopping or rightsizing it."
                ),
            )
        )
    return findings


def run(state: AgentState, client: CloudClient) -> dict:
    try:
        return {"idle_compute_findings": detect(client, state["raw_data"])}
    except Exception as exc:  # noqa: BLE001 - one detector must not crash the graph
        logger.exception("idle_compute detector failed")
        return {"idle_compute_findings": [], "errors": [f"idle_compute: {exc}"]}
