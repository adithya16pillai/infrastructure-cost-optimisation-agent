from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agent.detectors import old_snapshots
from app.aws.client import MockAwsClient
from app.gcp.client import MockGcpClient


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace(
        "+00:00", "Z"
    )


def _snap(snapshot_id: str, days: int, size_gb: int = 100) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "volume_id": None,
        "size_gb": size_gb,
        "start_time": _iso_days_ago(days),
        "description": "test",
    }


def test_threshold_is_180_days_strict():
    # 180-day threshold uses a strict ">": 179d is kept, 181d is flagged.
    raw = {"snapshots": [_snap("snap-young", 179), _snap("snap-old", 181)]}
    findings = old_snapshots.detect(MockAwsClient("us-east-1"), raw)

    ids = {f["resource_id"] for f in findings}
    assert ids == {"snap-old"}
    assert findings[0]["evidence"]["age_days"] >= 181
    # 100 GB @ $0.05/GB-mo = $5.00
    assert findings[0]["estimated_monthly_savings_cents"] == 500


def test_flags_four_old_mock_snapshots():
    client = MockAwsClient("us-east-1")
    raw = {"snapshots": client.list_snapshots()}
    findings = old_snapshots.detect(client, raw)

    ids = {f["resource_id"] for f in findings}
    assert ids == {"snap-0old001", "snap-0old002", "snap-0old003", "snap-0old004"}
    for f in findings:
        assert f["provider"] == "aws"
        assert f["finding_type"] == "old_snapshot"
        assert f["resource_type"] == "snapshot"
        assert f["evidence"]["age_days"] > 180


def test_gcp_old_snapshots_priced_and_tagged():
    client = MockGcpClient("us-central1")
    findings = old_snapshots.detect(client, {"snapshots": client.list_snapshots()})

    ids = {f["resource_id"] for f in findings}
    assert ids == {
        "snap-gce-old-001",
        "snap-gce-old-002",
        "snap-gce-old-003",
        "snap-gce-old-004",
    }
    by = {f["resource_id"]: f for f in findings}
    for f in findings:
        assert f["provider"] == "gcp"
    # 500 GB @ $0.026/GB-mo = $13.00
    assert by["snap-gce-old-001"]["estimated_monthly_savings_cents"] == 1300
