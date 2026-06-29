from __future__ import annotations

import time

import pytest

from app.agent.graph import build_graph, run_agent
from app.aws.client import MockAwsClient
from app.gcp.client import MockGcpClient
from app.models.enums import FindingType, ValidationStatus

VALID_STATUSES = {s.value for s in ValidationStatus}


@pytest.mark.parametrize(
    "client,provider,region",
    [
        (MockAwsClient("us-east-1"), "aws", "us-east-1"),
        (MockGcpClient("us-central1"), "gcp", "us-central1"),
    ],
)
def test_graph_end_to_end_counts_and_no_errors(client, provider, region):
    graph = build_graph(client)

    start = time.perf_counter()
    state = graph.invoke({"run_id": "test", "provider": provider})
    elapsed = time.perf_counter() - start

    agg = state["aggregated_findings"]
    assert len(agg) == 9  # mock seeds: 2 idle + 3 unattached + 4 old

    by_type = {}
    for f in agg:
        assert f["provider"] == provider
        by_type.setdefault(f["finding_type"], 0)
        by_type[f["finding_type"]] += 1
    assert by_type == {
        FindingType.IDLE_COMPUTE.value: 2,
        FindingType.UNATTACHED_DISK.value: 3,
        FindingType.OLD_SNAPSHOT.value: 4,
    }

    # Clean mock run records no detector errors.
    assert state["errors"] == []

    # Aggregated findings are sorted by savings, descending.
    savings = [f["estimated_monthly_savings_cents"] for f in agg]
    assert savings == sorted(savings, reverse=True)

    # Generous bound for the "under 1 second" acceptance criterion.
    assert elapsed < 2.0


@pytest.mark.parametrize(
    "provider,region",
    [("aws", "us-east-1"), ("gcp", "us-central1")],
)
def test_run_agent_returns_validated_findings(provider, region):
    findings = run_agent(run_id="t", provider=provider, mock=True, region=region)
    assert len(findings) == 9
    for f in findings:
        assert f["provider"] == provider
        assert f["validation_status"] in VALID_STATUSES
        assert f["validation_reasoning"].strip()
