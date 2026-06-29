from __future__ import annotations

from app.agent.detectors import unattached_disk
from app.aws.client import MockAwsClient
from app.gcp.client import MockGcpClient


def _aws() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def test_flags_only_available_disks():
    client = _aws()
    findings = unattached_disk.detect(client, {"disks": client.list_disks()})
    ids = {f["resource_id"] for f in findings}

    assert ids == {"vol-0unatt001", "vol-0unatt002", "vol-0unatt003"}
    # In-use disks are excluded.
    assert all("attach" not in i for i in ids)


def test_savings_match_pricing():
    client = _aws()
    by = {
        f["resource_id"]: f
        for f in unattached_disk.detect(client, {"disks": client.list_disks()})
    }
    # 500 GB gp3 @ $0.08/GB-mo = $40.00
    assert by["vol-0unatt001"]["estimated_monthly_savings_cents"] == 4000
    # 100 GB gp2 @ $0.10/GB-mo = $10.00
    assert by["vol-0unatt002"]["estimated_monthly_savings_cents"] == 1000
    # 250 GB gp3 @ $0.08/GB-mo = $20.00
    assert by["vol-0unatt003"]["estimated_monthly_savings_cents"] == 2000


def test_unknown_disk_type_defaults_to_base_price():
    client = _aws()
    raw = {
        "disks": [
            {
                "disk_id": "vol-weird",
                "size_gb": 100,
                "disk_type": "mystery",  # not in price table -> default 0.08
                "region": "us-east-1",
                "state": "available",
                "attached_instance_id": None,
                "create_time": "2025-01-01T00:00:00Z",
            }
        ]
    }
    findings = unattached_disk.detect(client, raw)
    assert findings[0]["estimated_monthly_savings_cents"] == 800  # 100 * 0.08 * 100
    assert findings[0]["evidence"]["created_days_ago"] > 0


def test_gcp_disks_tagged_provider_and_priced():
    client = MockGcpClient(region="us-central1")
    findings = unattached_disk.detect(client, {"disks": client.list_disks()})
    ids = {f["resource_id"] for f in findings}

    assert ids == {"pd-unatt-001", "pd-unatt-002", "pd-unatt-003"}
    by = {f["resource_id"]: f for f in findings}
    for f in findings:
        assert f["provider"] == "gcp"
        assert f["resource_type"] == "disk"
    # 500 GB pd-ssd @ $0.17/GB-mo = $85.00
    assert by["pd-unatt-001"]["estimated_monthly_savings_cents"] == 8500
    # 100 GB pd-balanced @ $0.10/GB-mo = $10.00
    assert by["pd-unatt-002"]["estimated_monthly_savings_cents"] == 1000
    # 250 GB pd-standard @ $0.04/GB-mo = $10.00
    assert by["pd-unatt-003"]["estimated_monthly_savings_cents"] == 1000
