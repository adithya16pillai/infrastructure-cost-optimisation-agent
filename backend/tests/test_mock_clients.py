from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.aws.client import MockAwsClient, RealAwsClient
from app.cloud.factory import build_client, get_client
from app.gcp.client import MockGcpClient, RealGcpClient


def _age_days(start_time: str) -> int:
    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


# --- AWS mock client -------------------------------------------------------

def _aws() -> MockAwsClient:
    return MockAwsClient(region="us-east-1")


def test_aws_compute_instances_are_identical_every_run():
    a = _aws().list_compute_instances()
    b = _aws().list_compute_instances()
    assert a == b
    assert len(a) == 5
    for inst in a:
        assert {
            "instance_id",
            "instance_type",
            "region",
            "state",
            "launch_time",
            "tags",
        } <= inst.keys()
        assert isinstance(inst["tags"], dict)


def test_aws_two_instances_are_idle_under_5_percent():
    client = _aws()
    running = [i for i in client.list_compute_instances() if i["state"] == "running"]
    idle = []
    for inst in running:
        series = client.get_cpu_utilization(inst["instance_id"], days=14)
        assert len(series) == 14  # daily averages over the window
        if sum(series) / len(series) < 5.0:
            idle.append(inst["instance_id"])
    assert set(idle) == {"i-0idle001", "i-0idle002"}


def test_aws_cpu_utilization_is_deterministic_and_noisy():
    client = _aws()
    s1 = client.get_cpu_utilization("i-0idle001", days=14)
    s2 = client.get_cpu_utilization("i-0idle001", days=14)
    assert s1 == s2
    assert len(set(s1)) > 1  # not flat zeros
    # Stopped instance reports no datapoints.
    assert client.get_cpu_utilization("i-0stop001", days=14) == []


def test_aws_disks_three_unattached():
    disks = _aws().list_disks()
    assert len(disks) == 6
    unattached = [d for d in disks if d["state"] == "available"]
    assert len(unattached) == 3
    for d in unattached:
        assert d["attached_instance_id"] is None


def test_aws_snapshots_four_older_than_180_days():
    snaps = _aws().list_snapshots()
    assert len(snaps) == 8
    old = [s for s in snaps if _age_days(s["start_time"]) > 180]
    assert len(old) == 4


def test_aws_pricing_methods():
    client = _aws()
    assert client.get_instance_hourly_cost("m5.large", "us-east-1") == 0.096
    # Unknown type or region returns 0.0 (detectors skip these).
    assert client.get_instance_hourly_cost("x9.huge", "us-east-1") == 0.0
    assert client.get_instance_hourly_cost("m5.large", "moon-base-1") == 0.0
    assert client.get_disk_gb_month_cost("gp2") == 0.10
    assert client.get_disk_gb_month_cost("mystery") == 0.08
    assert client.get_snapshot_gb_month_cost() == 0.05


# --- GCP mock client -------------------------------------------------------

def _gcp() -> MockGcpClient:
    return MockGcpClient(region="us-central1")


def test_gcp_shapes_match_normalized_contract():
    client = _gcp()
    assert client.provider == "gcp"

    instances = client.list_compute_instances()
    assert len(instances) == 5
    for inst in instances:
        assert {
            "instance_id",
            "instance_type",
            "region",
            "state",
            "launch_time",
            "tags",
        } <= inst.keys()
        assert inst["state"] in {"running", "stopped"}

    disks = client.list_disks()
    assert len(disks) == 6
    assert len([d for d in disks if d["state"] == "available"]) == 3
    for d in disks:
        assert {"disk_id", "size_gb", "disk_type", "state"} <= d.keys()

    snaps = client.list_snapshots()
    assert len([s for s in snaps if _age_days(s["start_time"]) > 180]) == 4


def test_gcp_pricing_methods():
    client = _gcp()
    assert client.get_instance_hourly_cost("n2-standard-4", "us-central1") == 0.19424
    assert client.get_instance_hourly_cost("unknown", "us-central1") == 0.0
    assert client.get_disk_gb_month_cost("pd-ssd") == 0.17
    assert client.get_disk_gb_month_cost("mystery") == 0.04
    assert client.get_snapshot_gb_month_cost() == 0.026


# --- factory ---------------------------------------------------------------

def test_build_client_selects_implementation():
    assert isinstance(build_client(provider="aws", mock=True, region="us-east-1"), MockAwsClient)
    assert isinstance(build_client(provider="aws", mock=False, region="us-east-1"), RealAwsClient)
    assert isinstance(build_client(provider="gcp", mock=True, region="us-central1"), MockGcpClient)
    assert isinstance(build_client(provider="gcp", mock=False, region="us-central1"), RealGcpClient)


def test_build_client_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_client(provider="azure", mock=True, region="x")


def test_get_client_uses_settings():
    settings = SimpleNamespace(
        cloud_provider="gcp",
        mock_cloud=True,
        default_region_for=lambda p: "us-central1",
    )
    assert isinstance(get_client(settings), MockGcpClient)


def test_real_gcp_client_methods_raise():
    client = RealGcpClient("us-central1")
    with pytest.raises(NotImplementedError):
        client.list_compute_instances()
