from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.aws.client import EBS_GB_MONTH_PRICE, AwsClient
from app.agent.state import AgentState, Finding
from app.models.enums import FindingType, ResourceType

logger = logging.getLogger(__name__)


def _created_days_ago(create_time: str | None) -> int | None:
    if not create_time:
        return None
    dt = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def detect(aws_client: AwsClient, raw_data: dict) -> list[Finding]:
    findings: list[Finding] = []

    for v in raw_data.get("ebs_volumes", []):
        if v["state"] != "available":
            continue

        rate = EBS_GB_MONTH_PRICE.get(v["volume_type"], 0.08)
        monthly_cents = round(v["size_gb"] * rate * 100)
        findings.append(
            Finding(
                finding_type=FindingType.UNATTACHED_EBS.value,
                resource_type=ResourceType.EBS.value,
                resource_id=v["volume_id"],
                region=v["region"],
                estimated_monthly_savings_cents=monthly_cents,
                evidence={
                    "size_gb": v["size_gb"],
                    "volume_type": v["volume_type"],
                    "created_days_ago": _created_days_ago(v.get("create_time")),
                },
                title=f"Unattached EBS volume {v['volume_id']} ({v['size_gb']} GB)",
                description=(
                    f"Volume {v['volume_id']} ({v['size_gb']} GB {v['volume_type']}) "
                    f"is in the 'available' state and attached to no instance. "
                    f"You are billed for it while it sits idle. Consider snapshotting "
                    f"then deleting it."
                ),
            )
        )
    return findings


def run(state: AgentState, aws_client: AwsClient) -> dict:
    try:
        return {"unattached_ebs_findings": detect(aws_client, state["raw_data"])}
    except Exception as exc:  # noqa: BLE001
        logger.exception("unattached_ebs detector failed")
        return {"unattached_ebs_findings": [], "errors": [f"unattached_ebs: {exc}"]}
