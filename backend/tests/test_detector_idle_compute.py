from __future__ import annotations

import pytest

from app.agent.detectors import idle_compute
from app.aws.client import MockAwsClient
from app.gcp.client import MockGcpClient


def _aws() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def _raw(client) -> dict:
    return {"compute_instances": client.list_compute_instances()}


def test_flags_only_running_low_cpu_instances():
    client = _aws()
    findings = idle_compute.detect(client, _raw(client))
    ids = {f["resource_id"] for f in findings}

    assert ids == {"i-0idle001", "i-0idle002"}
    # Busy, rightsizing-candidate, and stopped instances are excluded.
    assert "i-0busy001" not in ids
    assert "i-0peak001" not in ids
    assert "i-0stop001" not in ids


def test_savings_match_pricing():
    client = _aws()
    by = {f["resource_id"]: f for f in idle_compute.detect(client, _raw(client))}
    # m5.large @ $0.096/hr * 24 * 30 = $69.12 = 6912 cents
    assert by["i-0idle001"]["estimated_monthly_savings_cents"] == 6912
    # m5.xlarge @ $0.192/hr * 24 * 30 = $138.24 = 13824 cents
    assert by["i-0idle002"]["estimated_monthly_savings_cents"] == 13824


def test_evidence_shape():
    client = _aws()
    for f in idle_compute.detect(client, _raw(client)):
        assert f["provider"] == "aws"
        assert f["finding_type"] == "idle_compute"
        assert f["resource_type"] == "compute"
        ev = f["evidence"]
        assert ev["avg_cpu_percent"] < 5.0
        assert ev["days_observed"] == 14
        assert isinstance(ev["tags"], dict)


def test_instance_with_no_cpu_data_is_skipped():
    client = _aws()
    raw = {
        "compute_instances": [
            {
                "instance_id": "i-nometrics",  # no mock CPU profile -> []
                "instance_type": "m5.large",
                "region": "us-east-1",
                "state": "running",
                "launch_time": "2025-01-01T00:00:00Z",
                "tags": {},
            }
        ]
    }
    assert idle_compute.detect(client, raw) == []


def test_gcp_flags_idle_vms_and_tags_provider():
    client = MockGcpClient(region="us-central1")
    findings = idle_compute.detect(client, _raw(client))
    ids = {f["resource_id"] for f in findings}

    assert ids == {"gce-idle-001", "gce-idle-002"}
    for f in findings:
        assert f["provider"] == "gcp"
        assert f["finding_type"] == "idle_compute"
    # n2-standard-4 @ $0.19424/hr * 24 * 30 = $139.85 = 13985 cents
    by = {f["resource_id"]: f for f in findings}
    assert by["gce-idle-001"]["estimated_monthly_savings_cents"] == pytest.approx(
        round(0.19424 * 24 * 30 * 100)
    )
