from __future__ import annotations

import logging

from app.aws.client import AwsClient
from app.agent.state import AgentState, Finding
from app.config import settings
from app.models.enums import FindingType, ResourceType

logger = logging.getLogger(__name__)


def detect(aws_client: AwsClient, raw_data: dict) -> list[Finding]:
    threshold = settings.idle_cpu_percent_threshold
    lookback = settings.idle_lookback_days
    findings: list[Finding] = []

    for inst in raw_data.get("ec2_instances", []):
        if inst["state"] != "running":
            continue

        cpu = aws_client.get_ec2_cpu_utilization(inst["instance_id"], days=lookback)
        if len(cpu) == 0:
            continue  # no data, can't conclude

        avg = sum(cpu) / len(cpu)
        if avg >= threshold:
            continue

        hourly = aws_client.get_instance_hourly_cost(
            inst["instance_type"], inst["region"]
        )
        if hourly <= 0:
            logger.info("idle_ec2 skip %s (no price)", inst["instance_id"])
            continue

        monthly_cents = round(hourly * 24 * 30 * 100)
        tags = inst.get("tags", {})
        name = tags.get("Name")
        findings.append(
            Finding(
                finding_type=FindingType.IDLE_EC2.value,
                resource_type=ResourceType.EC2.value,
                resource_id=inst["instance_id"],
                region=inst["region"],
                estimated_monthly_savings_cents=monthly_cents,
                evidence={
                    "avg_cpu_percent": round(avg, 2),
                    "days_observed": len(cpu),
                    "instance_type": inst["instance_type"],
                    "tags": tags,
                },
                title=f"Idle EC2 instance {inst['instance_id']} ({inst['instance_type']})",
                description=(
                    f"Instance '{name or inst['instance_id']}' "
                    f"({inst['instance_type']}) averaged {avg:.1f}% CPU over the last "
                    f"{len(cpu)} days, below the {threshold:.0f}% idle threshold. "
                    f"Consider stopping or rightsizing it."
                ),
            )
        )
    return findings


def run(state: AgentState, aws_client: AwsClient) -> dict:
    try:
        return {"idle_ec2_findings": detect(aws_client, state["raw_data"])}
    except Exception as exc:  # noqa: BLE001 - one detector must not crash the graph
        logger.exception("idle_ec2 detector failed")
        return {"idle_ec2_findings": [], "errors": [f"idle_ec2: {exc}"]}
