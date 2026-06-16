"""LangGraph agent state and the canonical Finding shapes."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from typing_extensions import NotRequired


class Finding(TypedDict):
    finding_type: str  # "idle_ec2" | "unattached_ebs" | "old_snapshot"
    resource_type: str  # "ec2" | "ebs" | "snapshot"
    resource_id: str
    region: str
    estimated_monthly_savings_cents: int
    evidence: dict  # detector-specific facts
    # Additive (PRD 01 decision): human-facing copy for the dashboard cards.
    title: NotRequired[str]
    description: NotRequired[str]


class ValidatedFinding(Finding):
    validation_status: str  # "approve" | "needs_review" | "reject"
    validation_reasoning: str
    validation_raw: NotRequired[str | None]


class AgentState(TypedDict):
    run_id: str
    raw_data: NotRequired[dict]  # snapshot of what was fetched (traceability)

    # Each detector writes its own key so parallel updates don't conflict.
    idle_ec2_findings: NotRequired[list[Finding]]
    unattached_ebs_findings: NotRequired[list[Finding]]
    old_snapshot_findings: NotRequired[list[Finding]]

    aggregated_findings: NotRequired[list[Finding]]
    validated_findings: NotRequired[list[ValidatedFinding]]

    # Reducer so concurrently-failing detectors can both append safely.
    errors: Annotated[list[str], operator.add]
