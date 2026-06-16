"""Deterministic mock AWS data.

Hand-crafted fixtures that exercise every detector. EC2/EBS fixtures are fully
fixed (identical every run). Snapshot timestamps are computed relative to "now"
so the "older than 180 days" property holds no matter when the analysis runs;
their count is still deterministic.

CPU utilisation is generated with a fixed-seed RNG per instance, so it is
believable noise rather than flat zeros — but identical run-to-run.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

_SEED = 1337

# Per-instance daily-CPU profile as (low, high) percentage bounds. None => no
# datapoints (e.g. a stopped instance).
_CPU_PROFILE: dict[str, tuple[float, float] | None] = {
    "i-0idle001": (1.5, 3.5),   # idle candidate, avg < 5%
    "i-0idle002": (1.0, 4.0),   # idle candidate, avg < 5%
    "i-0busy001": (55.0, 75.0),  # busy
    "i-0peak001": (12.0, 38.0),  # rightsizing candidate: avg high, peak < 40%
    "i-0stop001": None,          # stopped, no metrics
}


def _days_ago_iso(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat().replace("+00:00", "Z")


def ec2_instances(region: str) -> list[dict]:
    return [
        {
            "instance_id": "i-0idle001",
            "instance_type": "m5.large",
            "region": region,
            "state": "running",
            "launch_time": "2025-01-04T08:12:00Z",
            "tags": {"Name": "legacy-batch-worker", "Environment": "prod"},
        },
        {
            "instance_id": "i-0idle002",
            "instance_type": "m5.xlarge",
            "region": region,
            "state": "running",
            "launch_time": "2025-03-21T14:03:00Z",
            "tags": {"Name": "staging-api-old", "Environment": "staging"},
        },
        {
            "instance_id": "i-0busy001",
            "instance_type": "c5.xlarge",
            "region": region,
            "state": "running",
            "launch_time": "2025-02-15T09:45:00Z",
            "tags": {"Name": "prod-web-1", "Environment": "prod"},
        },
        {
            "instance_id": "i-0peak001",
            "instance_type": "t3.medium",
            "region": region,
            "state": "running",
            "launch_time": "2025-04-10T11:30:00Z",
            "tags": {"Name": "prod-queue-consumer", "Environment": "prod"},
        },
        {
            "instance_id": "i-0stop001",
            "instance_type": "t3.small",
            "region": region,
            "state": "stopped",
            "launch_time": "2025-05-01T07:00:00Z",
            "tags": {"Name": "dev-sandbox", "Environment": "dev"},
        },
    ]


def cpu_utilization(instance_id: str, days: int) -> list[float]:
    """Daily-average CPU percentages, oldest first. Deterministic per instance."""
    profile = _CPU_PROFILE.get(instance_id)
    if profile is None:
        return []
    low, high = profile
    rng = random.Random(_SEED + sum(ord(c) for c in instance_id))
    return [round(rng.uniform(low, high), 1) for _ in range(days)]


def ebs_volumes(region: str) -> list[dict]:
    return [
        # 3 unattached (state "available").
        {
            "volume_id": "vol-0unatt001",
            "size_gb": 500,
            "volume_type": "gp3",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2024-11-02T10:00:00Z",
        },
        {
            "volume_id": "vol-0unatt002",
            "size_gb": 100,
            "volume_type": "gp2",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2025-01-18T16:20:00Z",
        },
        {
            "volume_id": "vol-0unatt003",
            "size_gb": 250,
            "volume_type": "gp3",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2025-02-27T12:05:00Z",
        },
        # 3 attached (state "in-use").
        {
            "volume_id": "vol-0attach001",
            "size_gb": 200,
            "volume_type": "gp3",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "i-0busy001",
            "create_time": "2025-02-15T09:45:00Z",
        },
        {
            "volume_id": "vol-0attach002",
            "size_gb": 50,
            "volume_type": "gp2",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "i-0peak001",
            "create_time": "2025-04-10T11:30:00Z",
        },
        {
            "volume_id": "vol-0attach003",
            "size_gb": 300,
            "volume_type": "io2",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "i-0idle001",
            "create_time": "2025-01-04T08:12:00Z",
        },
    ]


def ebs_snapshots() -> list[dict]:
    # 4 older than 180 days; 4 newer (all under 90 days).
    return [
        {
            "snapshot_id": "snap-0old001",
            "volume_id": "vol-0deleted01",
            "size_gb": 500,
            "start_time": _days_ago_iso(365),
            "description": "ami backup for legacy-batch-worker",
        },
        {
            "snapshot_id": "snap-0old002",
            "volume_id": None,
            "size_gb": 100,
            "start_time": _days_ago_iso(300),
            "description": "one-off manual snapshot",
        },
        {
            "snapshot_id": "snap-0old003",
            "volume_id": "vol-0deleted03",
            "size_gb": 250,
            "start_time": _days_ago_iso(250),
            "description": "pre-upgrade backup",
        },
        {
            "snapshot_id": "snap-0old004",
            "volume_id": "vol-0deleted04",
            "size_gb": 50,
            "start_time": _days_ago_iso(200),
            "description": "Backup before migration",
        },
        {
            "snapshot_id": "snap-0recent001",
            "volume_id": "vol-0attach001",
            "size_gb": 200,
            "start_time": _days_ago_iso(10),
            "description": "nightly backup",
        },
        {
            "snapshot_id": "snap-0recent002",
            "volume_id": "vol-0attach002",
            "size_gb": 80,
            "start_time": _days_ago_iso(30),
            "description": "nightly backup",
        },
        {
            "snapshot_id": "snap-0recent003",
            "volume_id": "vol-0attach003",
            "size_gb": 120,
            "start_time": _days_ago_iso(60),
            "description": "weekly backup",
        },
        {
            "snapshot_id": "snap-0recent004",
            "volume_id": "vol-0attach001",
            "size_gb": 40,
            "start_time": _days_ago_iso(85),
            "description": "weekly backup",
        },
    ]
