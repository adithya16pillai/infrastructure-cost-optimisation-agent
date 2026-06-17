from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.aws.client import (
    MockAwsClient,
    RealAwsClient,
    get_aws_client,
)


def _client() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def _age_days(start_time: str) -> int:
    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def test_ec2_instances_are_identical_every_run():
    a = _client().list_ec2_instances()
    b = _client().list_ec2_instances()
    assert a == b
    assert len(a) == 5
    for inst in a:
        assert {"instance_id", "instance_type", "region", "state", "launch_time", "tags"} <= inst.keys()
        assert isinstance(inst["tags"], dict)


def test_two_instances_are_idle_under_5_percent():
    client = _client()
    running = [i for i in client.list_ec2_instances() if i["state"] == "running"]
    idle = []
    for inst in running:
        series = client.get_ec2_cpu_utilization(inst["instance_id"], days=14)
        assert len(series) == 14  # daily averages over the window
        if sum(series) / len(series) < 5.0:
            idle.append(inst["instance_id"])
    assert set(idle) == {"i-0idle001", "i-0idle002"}


def test_cpu_utilization_is_deterministic_and_noisy():
    client = _client()
    s1 = client.get_ec2_cpu_utilization("i-0idle001", days=14)
    s2 = client.get_ec2_cpu_utilization("i-0idle001", days=14)
    assert s1 == s2
    assert len(set(s1)) > 1  # not flat zeros
    # Stopped instance reports no datapoints.
    assert client.get_ec2_cpu_utilization("i-0stop001", days=14) == []


def test_ebs_volumes_three_unattached():
    vols = _client().list_ebs_volumes()
    assert len(vols) == 6
    unattached = [v for v in vols if v["state"] == "available"]
    assert len(unattached) == 3
    for v in unattached:
        assert v["attached_instance_id"] is None
    assert {v["size_gb"] for v in vols} <= set(range(50, 501))


def test_snapshots_four_older_than_180_days():
    snaps = _client().list_ebs_snapshots()
    assert len(snaps) == 8
    old = [s for s in snaps if _age_days(s["start_time"]) > 180]
    assert len(old) == 4


def test_get_instance_hourly_cost():
    client = _client()
    assert client.get_instance_hourly_cost("m5.large", "us-east-1") == 0.096
    # Unknown type or region returns 0.0 (detectors skip these).
    assert client.get_instance_hourly_cost("x9.huge", "us-east-1") == 0.0
    assert client.get_instance_hourly_cost("m5.large", "moon-base-1") == 0.0


def test_get_aws_client_selects_implementation():
    mock_settings = SimpleNamespace(mock_aws=True, aws_region="us-east-1")
    real_settings = SimpleNamespace(mock_aws=False, aws_region="us-east-1")
    assert isinstance(get_aws_client(mock_settings), MockAwsClient)
    assert isinstance(get_aws_client(real_settings), RealAwsClient)
