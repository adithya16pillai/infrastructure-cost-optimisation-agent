from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.aws.client import SNAPSHOT_GB_MONTH_PRICE, AwsClient
from app.agent.state import AgentState, Finding
from app.config import settings
from app.models.enums import FindingType, ResourceType

logger = logging.getLogger(__name__)


def _age_days(start_time: str) -> int:
    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def detect(aws_client: AwsClient, raw_data: dict) -> list[Finding]:
    threshold = settings.snapshot_age_days_threshold
    findings: list[Finding] = []

    for snap in raw_data.get("ebs_snapshots", []):
        age_days = _age_days(snap["start_time"])
        if age_days <= threshold:
            continue

        size_gb = snap["size_gb"]
        monthly_cents = round(size_gb * SNAPSHOT_GB_MONTH_PRICE * 100)
        findings.append(
            Finding(
                finding_type=FindingType.OLD_SNAPSHOT.value,
                resource_type=ResourceType.SNAPSHOT.value,
                resource_id=snap["snapshot_id"],
                region=aws_client.region,
                estimated_monthly_savings_cents=monthly_cents,
                evidence={
                    "size_gb": size_gb,
                    "age_days": age_days,
                    "description": snap.get("description"),
                },
                title=f"Old EBS snapshot {snap['snapshot_id']} ({age_days} days old)",
                description=(
                    f"Snapshot {snap['snapshot_id']} ({size_gb} GB) is {age_days} days "
                    f"old, past the {threshold}-day retention threshold. "
                    f"Description: '{snap.get('description') or 'n/a'}'. "
                    f"Consider deleting it if it is no longer needed for recovery."
                ),
            )
        )
    return findings


def run(state: AgentState, aws_client: AwsClient) -> dict:
    try:
        return {"old_snapshot_findings": detect(aws_client, state["raw_data"])}
    except Exception as exc:  # noqa: BLE001
        logger.exception("old_snapshots detector failed")
        return {"old_snapshot_findings": [], "errors": [f"old_snapshots: {exc}"]}
