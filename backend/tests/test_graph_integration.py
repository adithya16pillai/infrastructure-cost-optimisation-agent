from __future__ import annotations

import time

from app.agent.graph import build_graph, run_agent
from app.aws.client import MockAwsClient
from app.models.enums import FindingType, ValidationStatus

VALID_STATUSES = {s.value for s in ValidationStatus}


def test_graph_end_to_end_counts_and_no_errors():
    graph = build_graph(MockAwsClient("us-east-1"))

    start = time.perf_counter()
    state = graph.invoke({"run_id": "test"})
    elapsed = time.perf_counter() - start

    agg = state["aggregated_findings"]
    assert len(agg) == 9  # matches PRD 02 mock seeds: 2 + 3 + 4

    by_type = {}
    for f in agg:
        by_type.setdefault(f["finding_type"], 0)
        by_type[f["finding_type"]] += 1
    assert by_type == {
        FindingType.IDLE_EC2.value: 2,
        FindingType.UNATTACHED_EBS.value: 3,
        FindingType.OLD_SNAPSHOT.value: 4,
    }

    # Clean mock run records no detector errors.
    assert state["errors"] == []

    # Aggregated findings are sorted by savings, descending.
    savings = [f["estimated_monthly_savings_cents"] for f in agg]
    assert savings == sorted(savings, reverse=True)

    # Generous bound for the "under 1 second" acceptance criterion.
    assert elapsed < 2.0


def test_run_agent_returns_validated_findings():
    findings = run_agent(run_id="t", mock=True, region="us-east-1")
    assert len(findings) == 9
    for f in findings:
        assert f["validation_status"] in VALID_STATUSES
        assert f["validation_reasoning"].strip()
