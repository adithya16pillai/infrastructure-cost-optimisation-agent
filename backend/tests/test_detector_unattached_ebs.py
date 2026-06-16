"""Unit tests for the unattached EBS detector."""
from __future__ import annotations

from app.agent.detectors import unattached_ebs
from app.aws.client import MockAwsClient


def _client() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def test_flags_only_available_volumes():
    client = _client()
    findings = unattached_ebs.detect(client, {"ebs_volumes": client.list_ebs_volumes()})
    ids = {f["resource_id"] for f in findings}

    assert ids == {"vol-0unatt001", "vol-0unatt002", "vol-0unatt003"}
    # In-use volumes are excluded.
    assert all("attach" not in i for i in ids)


def test_savings_match_pricing():
    client = _client()
    by = {
        f["resource_id"]: f
        for f in unattached_ebs.detect(client, {"ebs_volumes": client.list_ebs_volumes()})
    }
    # 500 GB gp3 @ $0.08/GB-mo = $40.00
    assert by["vol-0unatt001"]["estimated_monthly_savings_cents"] == 4000
    # 100 GB gp2 @ $0.10/GB-mo = $10.00
    assert by["vol-0unatt002"]["estimated_monthly_savings_cents"] == 1000
    # 250 GB gp3 @ $0.08/GB-mo = $20.00
    assert by["vol-0unatt003"]["estimated_monthly_savings_cents"] == 2000


def test_unknown_volume_type_defaults_to_gp3_price():
    client = _client()
    raw = {
        "ebs_volumes": [
            {
                "volume_id": "vol-weird",
                "size_gb": 100,
                "volume_type": "mystery",  # not in price table -> default 0.08
                "region": "us-east-1",
                "state": "available",
                "attached_instance_id": None,
                "create_time": "2025-01-01T00:00:00Z",
            }
        ]
    }
    findings = unattached_ebs.detect(client, raw)
    assert findings[0]["estimated_monthly_savings_cents"] == 800  # 100 * 0.08 * 100
    assert findings[0]["evidence"]["created_days_ago"] > 0
