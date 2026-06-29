from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

_SEED = 4242

# Per-instance daily-CPU profile as (low, high) percentage bounds. None => no
# datapoints (e.g. a TERMINATED instance, normalized to "stopped").
_CPU_PROFILE: dict[str, tuple[float, float] | None] = {
    "gce-idle-001": (1.0, 3.0),    # idle candidate, avg < 5%
    "gce-idle-002": (2.0, 4.5),    # idle candidate, avg < 5%
    "gce-busy-001": (50.0, 80.0),  # busy
    "gce-peak-001": (10.0, 35.0),  # rightsizing candidate
    "gce-stop-001": None,          # terminated, no metrics
}


def _days_ago_iso(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat().replace("+00:00", "Z")


def compute_instances(region: str) -> list[dict]:
    # GCP states (RUNNING / TERMINATED) are normalized to running / stopped.
    return [
        {
            "instance_id": "gce-idle-001",
            "instance_type": "n2-standard-4",
            "region": region,
            "state": "running",
            "launch_time": "2025-01-09T08:12:00Z",
            "tags": {"name": "legacy-etl-worker", "env": "prod"},
        },
        {
            "instance_id": "gce-idle-002",
            "instance_type": "e2-standard-2",
            "region": region,
            "state": "running",
            "launch_time": "2025-03-12T14:03:00Z",
            "tags": {"name": "staging-jobs-old", "env": "staging"},
        },
        {
            "instance_id": "gce-busy-001",
            "instance_type": "n2-standard-8",
            "region": region,
            "state": "running",
            "launch_time": "2025-02-20T09:45:00Z",
            "tags": {"name": "prod-api-1", "env": "prod"},
        },
        {
            "instance_id": "gce-peak-001",
            "instance_type": "e2-medium",
            "region": region,
            "state": "running",
            "launch_time": "2025-04-18T11:30:00Z",
            "tags": {"name": "prod-consumer", "env": "prod"},
        },
        {
            "instance_id": "gce-stop-001",
            "instance_type": "e2-small",
            "region": region,
            "state": "stopped",
            "launch_time": "2025-05-06T07:00:00Z",
            "tags": {"name": "dev-sandbox", "env": "dev"},
        },
    ]


def cpu_utilization(instance_id: str, days: int) -> list[float]:
    profile = _CPU_PROFILE.get(instance_id)
    if profile is None:
        return []
    low, high = profile
    rng = random.Random(_SEED + sum(ord(c) for c in instance_id))
    return [round(rng.uniform(low, high), 1) for _ in range(days)]


def disks(region: str) -> list[dict]:
    # GCP disks: an empty "users" list maps to state "available" (unattached).
    return [
        # 3 unattached.
        {
            "disk_id": "pd-unatt-001",
            "size_gb": 500,
            "disk_type": "pd-ssd",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2024-11-08T10:00:00Z",
        },
        {
            "disk_id": "pd-unatt-002",
            "size_gb": 100,
            "disk_type": "pd-balanced",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2025-01-22T16:20:00Z",
        },
        {
            "disk_id": "pd-unatt-003",
            "size_gb": 250,
            "disk_type": "pd-standard",
            "region": region,
            "state": "available",
            "attached_instance_id": None,
            "create_time": "2025-03-02T12:05:00Z",
        },
        # 3 attached.
        {
            "disk_id": "pd-attach-001",
            "size_gb": 200,
            "disk_type": "pd-ssd",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "gce-busy-001",
            "create_time": "2025-02-20T09:45:00Z",
        },
        {
            "disk_id": "pd-attach-002",
            "size_gb": 50,
            "disk_type": "pd-balanced",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "gce-peak-001",
            "create_time": "2025-04-18T11:30:00Z",
        },
        {
            "disk_id": "pd-attach-003",
            "size_gb": 300,
            "disk_type": "pd-standard",
            "region": region,
            "state": "in-use",
            "attached_instance_id": "gce-idle-001",
            "create_time": "2025-01-09T08:12:00Z",
        },
    ]


def snapshots() -> list[dict]:
    # 4 older than 180 days; 4 newer.
    return [
        {
            "snapshot_id": "snap-gce-old-001",
            "volume_id": "pd-deleted-01",
            "size_gb": 500,
            "start_time": _days_ago_iso(400),
            "description": "image backup for legacy-etl-worker",
        },
        {
            "snapshot_id": "snap-gce-old-002",
            "volume_id": None,
            "size_gb": 100,
            "start_time": _days_ago_iso(320),
            "description": "one-off manual snapshot",
        },
        {
            "snapshot_id": "snap-gce-old-003",
            "volume_id": "pd-deleted-03",
            "size_gb": 250,
            "start_time": _days_ago_iso(240),
            "description": "pre-upgrade backup",
        },
        {
            "snapshot_id": "snap-gce-old-004",
            "volume_id": "pd-deleted-04",
            "size_gb": 50,
            "start_time": _days_ago_iso(190),
            "description": "Backup before migration",
        },
        {
            "snapshot_id": "snap-gce-recent-001",
            "volume_id": "pd-attach-001",
            "size_gb": 200,
            "start_time": _days_ago_iso(12),
            "description": "nightly backup",
        },
        {
            "snapshot_id": "snap-gce-recent-002",
            "volume_id": "pd-attach-002",
            "size_gb": 80,
            "start_time": _days_ago_iso(35),
            "description": "nightly backup",
        },
        {
            "snapshot_id": "snap-gce-recent-003",
            "volume_id": "pd-attach-003",
            "size_gb": 120,
            "start_time": _days_ago_iso(65),
            "description": "weekly backup",
        },
        {
            "snapshot_id": "snap-gce-recent-004",
            "volume_id": "pd-attach-001",
            "size_gb": 40,
            "start_time": _days_ago_iso(88),
            "description": "weekly backup",
        },
    ]
