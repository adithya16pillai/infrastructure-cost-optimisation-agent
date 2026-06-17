from __future__ import annotations

from app.agent.detectors import idle_ec2
from app.aws.client import MockAwsClient


def _client() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def _raw(client) -> dict:
    return {"ec2_instances": client.list_ec2_instances()}


def test_flags_only_running_low_cpu_instances():
    client = _client()
    findings = idle_ec2.detect(client, _raw(client))
    ids = {f["resource_id"] for f in findings}

    assert ids == {"i-0idle001", "i-0idle002"}
    # Busy, rightsizing-candidate, and stopped instances are excluded.
    assert "i-0busy001" not in ids
    assert "i-0peak001" not in ids
    assert "i-0stop001" not in ids


def test_savings_match_pricing():
    client = _client()
    by = {f["resource_id"]: f for f in idle_ec2.detect(client, _raw(client))}
    # m5.large @ $0.096/hr * 24 * 30 = $69.12 = 6912 cents
    assert by["i-0idle001"]["estimated_monthly_savings_cents"] == 6912
    # m5.xlarge @ $0.192/hr * 24 * 30 = $138.24 = 13824 cents
    assert by["i-0idle002"]["estimated_monthly_savings_cents"] == 13824


def test_evidence_shape():
    client = _client()
    for f in idle_ec2.detect(client, _raw(client)):
        assert f["finding_type"] == "idle_ec2"
        assert f["resource_type"] == "ec2"
        ev = f["evidence"]
        assert ev["avg_cpu_percent"] < 5.0
        assert ev["days_observed"] == 14
        assert isinstance(ev["tags"], dict)


def test_instance_with_no_cpu_data_is_skipped():
    client = _client()
    raw = {
        "ec2_instances": [
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
    assert idle_ec2.detect(client, raw) == []
